# The Homebrew formula, kept here so it is reviewed with the code it installs.
#
# It is published by copying this file to `EDIFY-agents/homebrew-tap` as
# `Formula/edify.rb` with `url` and `sha256` pointed at the release being shipped.
# The release runbook has the two commands that produce both values.
#
# There are no `resource` blocks because the package has no dependencies — that is
# a deliberate property of this product, not an omission. If one is ever added,
# `brew update-python-resources edify` regenerates them.

class Edify < Formula
  include Language::Python::Virtualenv

  desc "Your coding agent is fast. Make it reliable"
  homepage "https://github.com/EDIFY-agents/edify_public"
  url "https://files.pythonhosted.org/packages/source/e/edify-cli/edify_cli-0.1.0.tar.gz"
  sha256 "0000000000000000000000000000000000000000000000000000000000000000"
  license :cannot_represent   # FSL-1.1-Apache-2.0 — source-available, no SPDX id

  depends_on "python@3.13"

  def install
    virtualenv_install_with_resources
  end

  test do
    # The version prints, and — the part that matters — the methodology tree really
    # is inside the artifact. A checkout on disk would hide this; there is none here.
    assert_match "edify", shell_output("#{bin}/edify version")

    (testpath/"src").mkpath
    (testpath/"pyproject.toml").write <<~TOML
      [project]
      name = "demo"
      dependencies = ["fastapi"]
    TOML
    (testpath/"src/app.py").write "def health():\n    return {\"ok\": True}\n"

    system bin/"edify", "init", "--yes"
    assert_predicate testpath/".edify/skills/planner.md", :exist?
    assert_match "src/app.py", shell_output("#{bin}/edify graph where health")
    system bin/"edify", "governance", "verify", "--exit-code"
  end
end
