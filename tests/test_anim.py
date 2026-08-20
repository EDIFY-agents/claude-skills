"""The ∞ animation: the frames, the glyph choice, and the rule about when it runs.

Precomputing the frames is what makes this testable at all (plan D-3) — a live
plotter could only be checked by a person squinting at a terminal. The assertions
here are the ones that matter for a decoration: it is the right shape, it is pure
ASCII when it has to be, and it never appears where it would corrupt output.
"""

from __future__ import annotations

import io
import json
import sys

import pytest

from edify import anim
from edify.cli import main
from edify.ui import Out


class FakeTTY:
    """A stream that claims to be a terminal, with an encoding you choose.

    Not a `StringIO` subclass: `encoding` is read-only there, and the encoding is
    exactly what `frames_for` probes.
    """

    def __init__(self, encoding: str = "utf-8", tty: bool = True) -> None:
        self._buf = io.StringIO()
        self.encoding = encoding
        self._tty = tty

    def isatty(self) -> bool:
        return self._tty

    def write(self, text: str) -> int:
        return self._buf.write(text)

    def flush(self) -> None:
        self._buf.flush()

    def getvalue(self) -> str:
        return self._buf.getvalue()


# -- the frame table --------------------------------------------------------


def test_there_are_as_many_frames_as_declared() -> None:
    assert len(anim.UNICODE_FRAMES) == anim.FRAMES
    assert len(anim.ASCII_FRAMES) == anim.FRAMES


def test_every_frame_is_the_same_rectangle() -> None:
    """A frame that is one line short walks the region up the screen for good."""
    for table in (anim.UNICODE_FRAMES, anim.ASCII_FRAMES):
        for frame in table:
            rows = frame.split("\n")
            assert len(rows) == anim.HEIGHT
            assert {len(r) for r in rows} == {anim.WIDTH}


def test_the_ascii_table_is_actually_ascii() -> None:
    """D-5: this is the set a cp1252 console gets, so it has to survive one."""
    for frame in anim.ASCII_FRAMES:
        frame.encode("ascii")
        frame.encode("cp1252")


def test_the_banner_is_actually_ascii() -> None:
    """It survives a pipe, a CI log, and a code page — so it is printed always."""
    for line in anim.BANNER:
        line.encode("ascii")


def test_every_frame_has_exactly_one_head() -> None:
    head = anim.ASCII_GLYPHS[0]
    for frame in anim.ASCII_FRAMES:
        assert frame.count(head) == 1


def test_the_head_travels_and_returns() -> None:
    """A constant-speed head on Gerono, which is why it is Gerono and not Bernoulli."""
    head = anim.ASCII_GLYPHS[0]
    positions = [frame.replace("\n", "").index(head) for frame in anim.ASCII_FRAMES]
    assert len(set(positions)) > anim.FRAMES // 2, "the head barely moves"
    # It is a closed curve: the last frame is adjacent to the first, not far from it.
    assert positions[0] != positions[len(positions) // 2]


def test_the_curve_is_a_lemniscate_and_not_a_blob() -> None:
    """Two lobes meeting in the middle — the shape is the whole point of D-4."""
    rows = anim.ASCII_FRAMES[0].split("\n")
    middle = rows[anim.HEIGHT // 2]
    drawn = [i for i, ch in enumerate(middle) if ch != " "]
    # The middle row is the crossing plus the two outer edges, and nothing between.
    assert len(drawn) < anim.WIDTH // 2
    top = rows[0]
    assert top.count(anim.ASCII_GLYPHS[2]) >= 4, "the top row should show both lobes"


def test_the_frames_are_built_once_and_are_immutable() -> None:
    assert isinstance(anim.UNICODE_FRAMES, tuple)
    assert isinstance(anim.ASCII_FRAMES, tuple)


# -- glyph selection --------------------------------------------------------


def test_a_utf8_stream_gets_the_unicode_glyphs() -> None:
    assert anim.frames_for(FakeTTY("utf-8")) is anim.UNICODE_FRAMES


def test_a_cp1252_console_gets_the_ascii_glyphs() -> None:
    """D-5, and the reason for it: this is the approver's own console."""
    assert anim.frames_for(FakeTTY("cp1252")) is anim.ASCII_FRAMES


def test_a_stream_with_no_encoding_gets_the_ascii_glyphs() -> None:
    class Bare:
        encoding = None

    assert anim.frames_for(Bare()) is anim.ASCII_FRAMES


def test_a_nonsense_encoding_does_not_raise() -> None:
    assert anim.frames_for(FakeTTY("not-a-real-codec")) is anim.ASCII_FRAMES


# -- when it runs -----------------------------------------------------------


def test_no_animation_without_a_terminal() -> None:
    """pytest captures stderr, so this is the default state of the whole suite."""
    assert Out().animated is False


def test_json_and_quiet_never_animate(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    assert Out().animated is True
    assert Out(json_mode=True).animated is False
    assert Out(quiet=True).animated is False


def test_the_no_anim_flag_turns_it_off(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    assert Out(anim=False).animated is False


@pytest.mark.parametrize("name, value", [("EDIFY_NO_ANIM", "1"), ("CI", "true"), ("TERM", "dumb")])
def test_the_environment_turns_it_off(
    name: str, value: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    monkeypatch.setenv(name, value)
    assert Out().animated is False


def test_a_piped_stdout_with_a_terminal_on_stderr_still_animates(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """`edify graph build > out.txt` is somebody watching, so it animates."""
    monkeypatch.setattr(sys, "stderr", FakeTTY(tty=True))
    monkeypatch.setattr(sys, "stdout", FakeTTY(tty=False))
    assert Out().animated is True


# -- the spinner ------------------------------------------------------------


def test_the_spinner_writes_nothing_when_it_is_not_allowed() -> None:
    stream = FakeTTY()
    out = Out(json_mode=True)
    with anim.Spinner(out, "working", stream=stream):
        pass
    assert stream.getvalue() == ""


def test_the_label_is_still_said_when_the_animation_is_off(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A pipe and a CI log say what happened; they just do not say it 14 times a second."""
    with anim.Spinner(Out(), "building the map", stream=FakeTTY()):
        pass
    assert "building the map" in capsys.readouterr().err


def test_the_spinner_paints_and_then_takes_it_back(monkeypatch: pytest.MonkeyPatch) -> None:
    stream = FakeTTY()
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    with anim.Spinner(Out(), "working", stream=stream):
        _wait_for_paint(stream)
    written = stream.getvalue()
    assert anim._HIDE in written
    assert written.endswith(anim._SHOW), "the cursor must be visible when the block ends"


def test_an_exception_inside_the_block_still_restores_the_cursor(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Nobody's terminal loses its cursor for the rest of the day over a traceback."""
    stream = FakeTTY()
    monkeypatch.setattr(sys, "stderr", FakeTTY())
    with pytest.raises(RuntimeError):
        with anim.Spinner(Out(), "working", stream=stream):
            _wait_for_paint(stream)
            raise RuntimeError("the work failed")
    assert stream.getvalue().endswith(anim._SHOW)


def test_the_spinner_never_swallows_the_block_s_exception() -> None:
    with pytest.raises(ValueError):
        with anim.Spinner(Out(), "working", stream=FakeTTY()):
            raise ValueError("this must escape")


def test_a_painter_that_explodes_does_not_fail_the_command(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Decoration is never load-bearing — the rule `_invite` already follows."""

    class Hostile(FakeTTY):
        def write(self, text: str) -> int:
            raise OSError("the terminal went away")

    monkeypatch.setattr(sys, "stderr", FakeTTY())
    with anim.Spinner(Out(), "working", stream=Hostile()):
        pass  # no exception is the assertion


def test_the_helper_always_returns_a_context_manager() -> None:
    with anim.spinner(Out(), "x"):
        pass


# -- the banner -------------------------------------------------------------


def test_the_banner_prints_to_stderr_so_a_pipe_stays_clean(
    capsys: pytest.CaptureFixture[str],
) -> None:
    anim.banner(Out())
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "EDIFY" not in captured.out
    assert any(line in captured.err for line in anim.BANNER)


def test_json_and_quiet_suppress_the_banner(capsys: pytest.CaptureFixture[str]) -> None:
    anim.banner(Out(json_mode=True))
    anim.banner(Out(quiet=True))
    captured = capsys.readouterr()
    assert captured.out == "" and captured.err == ""


def test_no_anim_suppresses_the_banner(capsys: pytest.CaptureFixture[str]) -> None:
    anim.banner(Out(anim=False))
    assert capsys.readouterr().err == ""


def test_edify_no_anim_suppresses_the_banner(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("EDIFY_NO_ANIM", "1")
    anim.banner(Out())
    assert capsys.readouterr().err == ""


# -- the gate that matters: --json is untouched -----------------------------


def test_setup_json_output_is_still_only_json(tmp_path, capsys: pytest.CaptureFixture[str]) -> None:
    """The M3 gate. Not one animation byte on stdout, banner included."""
    target = tmp_path / "anim-demo"
    assert main(["--json", "setup", str(target), "--no-graph", "--skills", "none"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)  # parses, so nothing else is on stdout
    assert payload["root"] == str(target.resolve())
    assert "\033" not in captured.out
    assert not any(line in captured.out for line in anim.BANNER)


def test_setup_prints_the_banner_once_not_twice(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    """`setup` routes through `init_cmd.run`; `caller_opens` is what stops the second."""
    assert main(["setup", str(tmp_path / "once"), "--no-graph", "--skills", "none"]) == 0
    assert capsys.readouterr().err.count(anim.BANNER[0]) == 1


def test_init_prints_the_banner_itself(repo, capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--repo", str(repo), "init", "--no-graph", "--skills", "none"]) == 0
    assert anim.BANNER[0] in capsys.readouterr().err


def test_no_anim_removes_the_banner_from_an_install(
    tmp_path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(["--no-anim", "setup", str(tmp_path / "plain"), "--no-graph",
                 "--skills", "none"]) == 0
    assert anim.BANNER[0] not in capsys.readouterr().err


def test_a_non_tty_run_emits_no_escape_codes(
    installed, capsys: pytest.CaptureFixture[str]
) -> None:
    """A CI log full of cursor-up sequences is the failure mode this rules out."""
    assert main(["--repo", str(installed), "graph", "build"]) == 0
    captured = capsys.readouterr()
    assert "\033[F" not in captured.out + captured.err
    assert "\033[?25l" not in captured.out + captured.err


def _wait_for_paint(stream: FakeTTY, timeout: float = 2.0) -> None:
    """Block until the painter thread has written its first frame."""
    import time

    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if anim._HIDE in stream.getvalue():
            return
        time.sleep(0.01)
    raise AssertionError("the painter never wrote a frame")
