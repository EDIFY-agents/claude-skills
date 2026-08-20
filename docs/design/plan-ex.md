# Implementation Plan — IRA7 BIOMECH (Phase 1 MVP + Phase 2-5 Roadmap)

**Feature ID:** `ira7-biomech-mvp`
**Trace ID:** IRA7-MVP-2026-05
**Created:** 2026-05-26 (scope expansion authored after spec.md/prd.md/research.md/data-model.md/contracts/ extensions)
**Status:** Draft — pending /spec human gate after analyze + checklist
**Source artifacts:** spec.md, prd.md, research.md, data-model.md, contracts/01..17.md, quickstart.md
**Downstream consumer:** `/task-manifest` (reads this file to decompose into tasks.md with snippet_refs into the artifacts above)

This plan is the architectural handoff document. It tells `/task-manifest` exactly how to decompose the spec into tasks: which phases, what order, which work can parallelize, which files are affected, and where in the code (once code exists) the implementation must integrate. It does NOT write code; it sequences the work and embeds snippet seeds for `/tasks` and `/implement` to consume without exploration.

---

## 1. Phase Sequencing (per CONST-INV-008)

12 milestones across 5 phases. Phase gates must pass before the next phase begins.

```
Phase 1 (MVP):  M1 → M2 → M3 ↘
                M3 → M4    ↘  → M6 → ✅ Phase 1 gate (SC-1..SC-10)
                M3 → M5    ↗
                                ↓
Phase 2:        M7 (parallel-eligible with M8) → ✅ Phase 2 gate (SC-11..SC-14)
                M8
                                ↓
Phase 3:        M9 → M10 → ✅ Phase 3 gate (SC-15..SC-19)
                                ↓
Phase 4:        M11 → ✅ Phase 4 gate (SC-20..SC-23)
                                ↓
Phase 5:        M12 → ✅ Phase 5 gate (SC-24..SC-25) → ✅ Roadmap complete
```

**Dependency rules:**
- M1 must complete before M2 (CameraX capture screen + Calibration row schema are M2 inputs).
- M2 must complete before M3, M4, M5 (BlazePose + filter + COM are pillar prerequisites).
- M3, M4, M5 can run in parallel after M2.
- M6 must come last in Phase 1 (consumes all upstream Metric rows for UI + export).
- Phase 2 M7 + M8 can run in parallel after Phase 1 gate (M7 builds frontal capture stack; M8 builds penultimate + initiation + F-v-P which depend only on M3 pipeline + new metric computation).
- M9 strictly precedes M10 (Pillar D requires 3D triangulation output from M9).
- M11 precedes M12 (Phase 5 biomech overlay requires Phase 4 tracking + focus).

---

## 2. Per-Milestone Plan

### 2.1 M1 — Capture + Calibration Skeleton *[Phase 1]*

**Goal:** CameraX capture screen (30/120/240 fps), static shank-length calibration, basic Session/Trial creation, record-blocked-until-calibrated gate.

**FRs covered:** FR-001, FR-002, FR-005, partial FR-029.
**Gate:** SC-4 (three back-to-back calibrations within ±5% std).
**Size:** M.
**Affected files (estimated, prefix `app/src/main/`):**
- `java/com/ira7/biomech/Ira7Application.kt`
- `java/com/ira7/biomech/di/AppModule.kt`
- `java/com/ira7/biomech/capture/CaptureScreen.kt`
- `java/com/ira7/biomech/capture/CameraAdapter.kt`
- `java/com/ira7/biomech/capture/CalibrationScreen.kt`
- `java/com/ira7/biomech/data/db/Ira7Database.kt`
- `java/com/ira7/biomech/data/db/entities/{Athlete,Session,Calibration,Trial}Entity.kt`
- `java/com/ira7/biomech/data/db/dao/{Athlete,Session,Calibration,Trial}Dao.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV1.kt`
- `AndroidManifest.xml`
- `res/xml/network_security_config_block_all.xml`
- `build.gradle.kts`

**Domains:** mobile, vision (calibration shank detection), data.

**Snippet seeds for /task-manifest:**
- `contracts/01-capture-and-calibration.md` line 1–end (capture + calibration contract)
- `data-model.md §2.1, §2.2, §2.3, §2.4` (Athlete, Session, Calibration, Trial entities)
- `research.md §2, §6, §7, §9` (calibration, fps, auto-zoom, CameraX decisions)
- `spec.md FR-001, FR-002, FR-004, FR-005` (capture FRs)

### 2.2 M2 — BlazePose Inference + Signal Processing *[Phase 1]*

**Goal:** Bundled MediaPipe BlazePose, per-frame inference, outlier rejection, Butterworth filter, central-diff differentiation, per-frame re-scaling, out-of-plane motion check, Frame persistence.

**FRs covered:** FR-003, FR-006, FR-007, FR-008, FR-009, FR-010, partial FR-004.
**Gate:** SC-5 (≥85% retention clean, ≥95% rejection occluded).
**Size:** L.
**Affected files (estimated):**
- `assets/models/blazepose.tflite` (bundled model)
- `java/com/ira7/biomech/vision/BlazePoseInferenceService.kt`
- `java/com/ira7/biomech/vision/OutlierRejection.kt`
- `java/com/ira7/biomech/vision/PerFrameRescaler.kt`
- `java/com/ira7/biomech/vision/InPlaneMotionDetector.kt`
- `java/com/ira7/biomech/biomech/ButterworthFilter.kt`
- `java/com/ira7/biomech/biomech/CentralDiffDifferentiator.kt`
- `java/com/ira7/biomech/biomech/Anthropometry.kt` (de Leva bundled table)
- `java/com/ira7/biomech/biomech/ComComputer.kt`
- `java/com/ira7/biomech/data/db/entities/FrameEntity.kt` (full DAO)
- `java/com/ira7/biomech/data/db/dao/FrameDao.kt`

**Domains:** vision, biomech, data.

**Snippet seeds:**
- `contracts/02-pose-and-signal-pipeline.md`
- `contracts/03-com-and-anthropometry.md`
- `data-model.md §2.5` (Frame entity)
- `research.md §1, §3, §4, §5` (BlazePose, filter, outlier, BSP decisions)

### 2.3 M3 — Pillar A (Sprint & Acceleration) *[Phase 1]*

**FRs covered:** FR-011..FR-016, partial FR-024.
**Gate:** SC-3 (GCT ±10 ms vs frame-by-frame), SC-8 (low-fps blocking 100%).
**Size:** M.
**Affected files:**
- `java/com/ira7/biomech/biomech/pillara/{TrunkLeanComputer,ShinAngleComputer,ComVelocityComputer,StepLengthFrequencyComputer,GctComputer,KneeDriveComputer}.kt`
- `java/com/ira7/biomech/biomech/pillara/PillarAComputer.kt` (aggregator)
- `java/com/ira7/biomech/biomech/EventDetector.kt` (touchdown/toe-off)
- `java/com/ira7/biomech/biomech/LsiComputer.kt`

**Snippet seeds:** `contracts/04-pillar-a-sprint.md`, `data-model.md §4 Pillar A` canonical metrics.

### 2.4 M4 — Pillar B (Plyometric / Elastic) *[Phase 1]*

**FRs covered:** FR-018..FR-021, partial FR-024.
**Size:** M.
**Affected files:**
- `java/com/ira7/biomech/biomech/pillarb/{RsiComputer,LegStiffnessComputer,JumpHeightComputer,AnkleStiffnessComputer}.kt`
- `java/com/ira7/biomech/biomech/pillarb/PillarBComputer.kt`

**Snippet seeds:** `contracts/05-pillar-b-plyometrics.md`.

### 2.5 M5 — Pillar C (Sagittal) + LSI Roll-up *[Phase 1]*

**FRs covered:** FR-022, FR-023, completion of FR-024.
**Size:** S.
**Affected files:**
- `java/com/ira7/biomech/biomech/pillarc/{DecelerationComputer,ApproachExitVelocityComputer}.kt`
- `java/com/ira7/biomech/biomech/pillarc/PillarCSagittalComputer.kt`

**Snippet seeds:** `contracts/06-pillar-c-deceleration.md`.

### 2.6 M6 — UI Scrubber + Storage + Export + Drill Catalog + "What's Missing" *[Phase 1]*

**FRs covered:** FR-025..FR-035.
**Gate:** SC-1, SC-2, SC-6, SC-9, SC-10.
**Size:** L.
**Affected files (high-level):**
- `java/com/ira7/biomech/ui/analysis/{FrameScrubberScreen,SynchronizedDataPanel,SessionCompareScreen}.kt`
- `java/com/ira7/biomech/rules/RuleEngine.kt`
- `java/com/ira7/biomech/data/db/dao/{Metric,RuleEvaluation,DrillPreset}Dao.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV{3,4,5,6}.kt`
- `java/com/ira7/biomech/data/export/{CsvExporter,JsonExporter}.kt`
- `java/com/ira7/biomech/ui/library/VideoLibraryScreen.kt`
- `assets/rule-catalog.json`, `assets/drill-presets.json`

**Snippet seeds:** contracts/07–12 + research §11, §12, §13.

---

### 2.7 M7 — Phase 2 Frontal Capture Stack *[Phase 2]*

**Goal:** Two-Phone (sagittal + frontal) topology, FR-045 minimal mode (audio sync only), FR-037 2D-proxy FPPA, FR-038 trunk lean + lateral plant distance.

**FRs covered:** FR-001 (frontal-view extension), FR-005, FR-037 (2D proxy), FR-038, FR-045 (minimal mode), partial FR-024 (LSI on FPPA).
**Gate:** SC-11 (FPPA repeatability ±3°), SC-14 (two-phone concurrent capture 30-rep no-drop), SC-6 re-run on multiphone variant manifest.
**Size:** L.
**Domains:** mobile, vision.
**Migration:** V8 (Metric.quality_flag column for FPPA rotation flag; FPPA + lateral_plant metric name CHECK extensions).
**Affected files (new + extended):**
- `java/com/ira7/biomech/capture/MultiPhoneCaptureCoordinator.kt`
- `java/com/ira7/biomech/capture/HotspotJoinFlow.kt`
- `java/com/ira7/biomech/capture/SyncEventGenerator.kt`
- `java/com/ira7/biomech/sync/AudioCrossCorrelator.kt`
- `java/com/ira7/biomech/data/db/entities/{MultiCameraRigEntity,ClipSyncEventEntity}.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV8.kt`
- `java/com/ira7/biomech/biomech/pillarc/frontal/{FppaComputer,TrunkLeanComputer,LateralPlantDistanceComputer,RotationFlagDetector}.kt`
- `java/com/ira7/biomech/biomech/pillarc/frontal/PillarCFrontalComputer.kt`
- `java/com/ira7/biomech/ui/analysis/TwoViewSideBySideScreen.kt`
- `AndroidManifest.xml` (multiphone flavor)
- `res/xml/network_security_config_rfc1918_only.xml`
- `build.gradle.kts` (product flavor `multiphone`)
- `app/buildSrc/.../VerifyNoPublicEndpoint.kt` (CI gradle task)

**Snippet seeds:**
- `contracts/14-pillar-c-frontal.md` (FPPA + trunk lean + lateral plant)
- `contracts/15-multi-phone-3d.md §2.1` (FR-045 minimal mode)
- `data-model.md §13.1, §13.2, §13.3, §13.5, §15.2`
- `research.md §19.2, §19.10, §19.11`

### 2.8 M8 — Phase 2 Penultimate-Step + Initiation + F-v-P *[Phase 2]*

**FRs covered:** FR-017, FR-036, FR-039.
**Gate:** SC-12 (penultimate detector accuracy), SC-13 (F-v-P reference range).
**Size:** M.
**Affected files:**
- `java/com/ira7/biomech/biomech/pillarc/frontal/PenultimateStepDetector.kt`
- `java/com/ira7/biomech/biomech/pillarc/frontal/PenultimateBrakingComputer.kt`
- `java/com/ira7/biomech/biomech/pillarc/frontal/InitiationLatencyComputer.kt`
- `java/com/ira7/biomech/biomech/pillara/FvProfileComputer.kt`
- `java/com/ira7/biomech/biomech/pillara/ExponentialFitter.kt`
- `assets/rule-catalog.json` (extend with FVP reference ranges + double-flag rule)
- `java/com/ira7/biomech/ui/analysis/FvProfileChart.kt`

**Snippet seeds:**
- `contracts/13-pillar-a-fv-profile.md`
- `contracts/14-pillar-c-frontal.md §2.1, §2.4`
- `data-model.md §15.1, §15.2`
- `research.md §19.1`

### 2.9 M9 — Phase 3 Multi-Phone Sync + Camera Calibration + 3D Triangulation *[Phase 3]*

**FRs covered:** FR-045 (full), FR-046, FR-047.
**Gate:** SC-15 (sync ≤ 5 ms), SC-16 (calibration ≤ 3 px), SC-17 (3D inter-joint ±2 cm).
**Size:** L.
**Migration:** V7 (Trial.topology + Trial.multi_camera_rig_id + Trial.sync_residual_ms + Trial.triangulation_blocked + Trial.pose_dimensionality columns; Frame.camera_index + Frame.pose_model_used columns; MultiCameraRig + CameraExtrinsics + ClipSyncEvent + Pose3DFrame tables).
**Affected files:**
- `assets/models/rtmpose_halpe26.tflite`
- `assets/models/yolov8_small_detector.tflite` (shared with M11)
- `assets/calibration/charuco_6x8.pdf`
- `java/com/ira7/biomech/vision/rtmpose/RtmPoseInferenceService.kt`
- `java/com/ira7/biomech/vision/yolo/YoloDetector.kt`
- `java/com/ira7/biomech/calibration/CharucoIntrinsicsCalibrator.kt`
- `java/com/ira7/biomech/calibration/ExtrinsicsSolver.kt`
- `java/com/ira7/biomech/triangulation/DltTriangulator.kt`
- `java/com/ira7/biomech/triangulation/RansacInlierSelector.kt`
- `java/com/ira7/biomech/transfer/LocalFileServer.kt` (Ktor or NanoHTTPD on hotspot)
- `java/com/ira7/biomech/transfer/ChunkedClipUploader.kt`
- `java/com/ira7/biomech/data/db/entities/{CameraExtrinsicsEntity,Pose3DFrameEntity}.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV7.kt`
- `java/com/ira7/biomech/ui/setup/RigSetupWizard.kt`
- `java/com/ira7/biomech/ui/setup/CalibrationScreen.kt`
- `java/com/ira7/biomech/ui/setup/SyncTestScreen.kt`

**Snippet seeds:**
- `contracts/15-multi-phone-3d.md` (entire file)
- `data-model.md §13.3..§13.7, §16` (Phase 3 schema + migration)
- `research.md §19.3, §19.4, §19.5, §19.6, §19.10`

### 2.10 M10 — Phase 3 Pillar D Kinetics + Honest Labeling *[Phase 3]*

**FRs covered:** FR-037 (3D path), FR-040..FR-044.
**Gate:** SC-18 (estimated-label coverage 100%), SC-19 (error-band disclosure 100%).
**Size:** L.
**Migration:** V9 (Metric.unit CHECK extension for newtons_per_kg, watts_per_kg, etc.; Pillar D metric name extensions).
**Affected files:**
- `java/com/ira7/biomech/biomech/pillard/JointAngleComputer.kt`
- `java/com/ira7/biomech/biomech/pillard/JointOmegaComputer.kt`
- `java/com/ira7/biomech/biomech/pillard/InverseDynamicsComputer.kt`
- `java/com/ira7/biomech/biomech/pillard/KinematicGrfEstimator.kt`
- `java/com/ira7/biomech/biomech/pillard/JointPowerWorkComputer.kt`
- `java/com/ira7/biomech/biomech/pillard/EnergyLabeler.kt`
- `java/com/ira7/biomech/biomech/pillarc/frontal/KneeAbduction3dComputer.kt` (FR-037 3D path)
- `java/com/ira7/biomech/ui/analysis/PillarDScreen.kt`
- `java/com/ira7/biomech/ui/analysis/EstimatedBadge.kt` (reusable UI component for CONST-INV-002)
- `assets/copy/pillar-d-disclosures.json`
- `java/com/ira7/biomech/data/db/migrations/MigrationV9.kt`

**Snippet seeds:**
- `contracts/16-pillar-d-kinetics.md` (entire file)
- `data-model.md §15.3, §16`
- `research.md §19.7`

### 2.11 M11 — Phase 4 Match Detection + Tracking + Homography + Basic Stats *[Phase 4]*

**FRs covered:** FR-033 (consent gate live), FR-048, FR-049, FR-050, FR-051 (Phase 4 subset).
**Gate:** SC-20 (MOTA ≥ 0.6), SC-21 (homography ≤ 2 m midfield), SC-22 (consent gate 100%), SC-23 (offline operability).
**Size:** XL.
**Migration:** V10 (Session.match_id + Session.consent_dismissed_at columns; Match + PlayerTrack + PitchHomography + MatchPlayerStats + PlayerFocus tables).
**Affected files (high-level):**
- `assets/models/yolov8_pose.tflite` (shared with M9)
- `assets/models/tvcalib_pitch.tflite`
- `java/com/ira7/biomech/match/ConsentGate.kt`
- `java/com/ira7/biomech/match/MatchCaptureFlow.kt`
- `java/com/ira7/biomech/match/detection/YoloMatchDetector.kt`
- `java/com/ira7/biomech/match/tracking/ByteTracker.kt`
- `java/com/ira7/biomech/match/team/HsvTeamAssigner.kt`
- `java/com/ira7/biomech/match/homography/PitchKeypointDetector.kt`
- `java/com/ira7/biomech/match/homography/HomographySolver.kt`
- `java/com/ira7/biomech/match/homography/KalmanOpticalFlowPropagator.kt`
- `java/com/ira7/biomech/match/focus/PlayerFocusManager.kt`
- `java/com/ira7/biomech/match/focus/ReIdentifier.kt`
- `java/com/ira7/biomech/match/stats/PerPlayerStatsComputer.kt`
- `java/com/ira7/biomech/data/db/entities/{MatchEntity,PlayerTrackEntity,PitchHomographyEntity,MatchPlayerStatsEntity,PlayerFocusEntity}.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV10.kt`
- `java/com/ira7/biomech/ui/match/{MatchCaptureScreen,PlayerGridView,PitchHeatmapView,MatchTimelineStrip,FocusedPlayerPanel}.kt`

**Snippet seeds:**
- `contracts/17-match-module.md §1, §2.1..§2.5`
- `data-model.md §14`
- `research.md §19.8, §19.12`

### 2.12 M12 — Phase 5 Match Event Stats + Focused-Player Biomech Overlay *[Phase 5]*

**FRs covered:** FR-051 (Phase 5 subset), FR-052.
**Gate:** SC-24 (visibility ≥ 60%), SC-25 (indicative badge 100%).
**Size:** L.
**Migration:** V11 (MatchEvent table; MatchPlayerStats event-stat columns).
**Affected files:**
- `java/com/ira7/biomech/match/events/{PassDetector,ShotDetector,PossessionTracker,OneVsOneDetector}.kt`
- `java/com/ira7/biomech/match/events/EventStatsComputer.kt`
- `java/com/ira7/biomech/match/biomech/FocusedPlayerBlazePoseRoi.kt`
- `java/com/ira7/biomech/match/biomech/MatchBiomechOverlayComputer.kt`
- `java/com/ira7/biomech/data/db/entities/MatchEventEntity.kt`
- `java/com/ira7/biomech/data/db/migrations/MigrationV11.kt`
- `java/com/ira7/biomech/ui/match/MatchBiomechOverlayScreen.kt`
- `java/com/ira7/biomech/ui/match/IndicativeBadge.kt` (reusable UI component)
- Annotate every match-overlay Metric row with `pose_dimensionality = 'match_2d_roi'`

**Snippet seeds:**
- `contracts/17-match-module.md §2.5, §2.6`
- `data-model.md §14.5, §14.7, §15.5`
- `research.md §19.9`

---

## 3. Cross-Cutting Concerns by Phase

### 3.1 Build Variant Strategy

- `singlephone` variant (default, used by Phase 1 + Phase 2 frontal-only): manifest declines `INTERNET`; `network_security_config_block_all.xml`.
- `multiphone` variant (Phase 3+): manifest declares `INTERNET` scoped via `network_security_config_rfc1918_only.xml` to RFC1918 subnets; build-time `verifyNoPublicEndpoint` task fails CI on non-RFC1918 references.

M7 introduces the variant infrastructure even though it only minimally uses sync. M9 onward fully exercises it.

### 3.2 Migration Strategy

Phase 1 owns V1..V6 (per tasks.md §Migration Version Owner Contract). Phase 2-5 own V7..V11:

| V | Phase | Milestone | Schema additions |
|---|---|---|---|
| V7 | 3 | M9 | Trial Phase 3 columns + Frame Phase 3 columns + MultiCameraRig + CameraExtrinsics + ClipSyncEvent + Pose3DFrame |
| V8 | 2 | M7 | Metric.quality_flag column + FPPA/lateral metric name CHECK extension |
| V9 | 3 | M10 | Metric.unit CHECK extension for Pillar D units; Pillar D metric name extension |
| V10 | 4 | M11 | Session match columns + Match/PlayerTrack/PitchHomography/MatchPlayerStats/PlayerFocus tables |
| V11 | 5 | M12 | MatchEvent table + MatchPlayerStats event-stat columns |

Migration version order is V1..V11 numerically. V8 is allocated to M7 (Phase 2) but applied in numeric order, so a fresh install of a Phase-3 build applies V1..V9 in order (V8 before V9).

### 3.3 Pose Model Asset Bundling

- Phase 1+2+5 (training + match focused ROI): BlazePose `.tflite` (~10 MB) bundled in `singlephone` variant and shared by `multiphone` variant.
- Phase 3 (3D pipeline): RTMPose Halpe-26 `.tflite` (~25 MB) bundled only in `multiphone` variant.
- Phase 4+5 (match detection): YOLOv8/YOLO11-pose small-class `.tflite` (~10 MB) + TVCalib pitch keypoint `.tflite` (~15 MB) bundled in `multiphone` variant.

Total asset bundle: `singlephone` ~10 MB; `multiphone` ~60 MB additional.

### 3.4 UI Reusable Components (introduced incrementally)

- `EstimatedBadge` (introduced at M10 for Pillar D, reused at M8 for F-v-P).
- `IndicativeBadge` (introduced at M12 for match biomech overlay).
- `TwoViewSideBySideScreen` (introduced at M7).
- Existing `FrameScrubberScreen` extended at M8 + M10 + M12 for per-phase metric overlays.

### 3.5 Constitutional Enforcement Gates per Phase

| Phase | Critical invariant check | Gate event |
|---|---|---|
| 1 | CONST-INV-001, -002, -003 (stub), -004, -005, -006, -007 (BlazePose), -008 | M6 gate: SC-6 + SC-7 + SC-9 + SC-10 |
| 2 | CONST-INV-001 (multiphone manifest scoped), -002 (2D proxy label + FPPA-estimated label), -005 (frontal pre-conditions), -007 (BlazePose extension) | M7 gate: SC-6 re-run on multiphone variant; M8 gate: SC-13 |
| 3 | CONST-INV-001 (multiphone scoped), -002 (Pillar D estimated label + ±10–20% disclosure), -005 (sync gate + calibration gate + triangulation block), -007 (RTMPose binding) | M9 gate: SC-15, SC-16, SC-17; M10 gate: SC-18, SC-19 |
| 4 | CONST-INV-001 (no internet during match), -003 (consent gate enforced), -005 (homography degraded tag), -007 (YOLO11-pose binding) | M11 gate: SC-22 + SC-23 + SC-6 re-run |
| 5 | CONST-INV-002 (indicative badge), -007 (BlazePose on focused ROI binding) | M12 gate: SC-25 |

---

## 4. Parallelization Opportunities

| Phase | Within-phase parallel work |
|---|---|
| 1 | M3 + M4 + M5 can run concurrently after M2 (different Pillar computers in different packages) |
| 2 | M7 (frontal capture stack) + M8 (penultimate/initiation/F-v-P) can run concurrently after Phase 1 gate (different domain: M7 is infrastructure, M8 is compute) |
| 3 | M9 (sync + calibration + triangulation) and M10 (Pillar D) are strictly sequential (M10 consumes M9 output) |
| 4 | M11 sub-tasks: detection + tracking + team-assign can run concurrently with homography + per-player stats (different files; aggregator in single integration task) |
| 5 | M12 sub-tasks: event detection + biomech overlay can run concurrently (different files; integration task surfaces both in focused-player panel) |

Cross-phase parallelization is forbidden by CONST-INV-008 phase sequencing.

---

## 5. Estimated Affected-File Count per Phase

| Phase | Milestone | Estimated new files | Estimated extended files |
|---|---|---|---|
| 1 | M1..M6 | ~60 | ~5 (manifest, build.gradle) |
| 2 | M7..M8 | ~25 | ~6 (CaptureScreen, AndroidManifest variant, rule-catalog) |
| 3 | M9..M10 | ~35 | ~3 (FrameScrubberScreen, AnalysisScreen) |
| 4 | M11 | ~25 | ~5 |
| 5 | M12 | ~10 | ~3 |
| **Total** | **M1..M12** | **~155** | **~22** |

---

## 6. Risks (Phase 2-5 specific; carried from spec.md §11)

| Risk | Phase | Mitigation in plan |
|---|---|---|
| R-10 (FPPA 2D-proxy rotation bias) | 2 | M7 includes RotationFlagDetector + quality_flag column (V8 migration) |
| R-11 (F-v-P body mass error) | 2 | M8 includes reference-range deviation flag (SC-13); F-v-P "estimated" badge |
| R-12 (multi-camera calibration error) | 3 | M9 enforces calibration-quality gate (≤3 px reprojection); re-capture flow on failure |
| R-13 (homography failure on camera pan) | 4 | M11 includes KalmanOpticalFlowPropagator with extrapolated tagging (CONST-INV-005 spirit) |
| R-14 (ByteTrack ID switches on jersey similarity) | 4 | M11 includes coach team-override UX (US-035); jersey-number OCR deferred to Phase 4b polish |
| R-15 (multi-phone manifest INTERNET nuance) | 3, 4 | Variant build flavor + network-security-config + verifyNoPublicEndpoint CI gate (M7 introduces, M9 fully exercises) |

---

## 7. Handoff Seeds for /task-manifest

For each milestone, `/task-manifest` should produce task entries with `snippet_refs` pointing to the artifacts below. Each ref is `(file, line_start, line_end, reason)`.

### M7 handoff seeds (per task-manifest consumption)

```json
{
  "milestone": "M7",
  "snippet_refs": [
    {"file": "specs/ira7-biomech-mvp/contracts/14-pillar-c-frontal.md", "line_start": 1, "line_end": 100, "reason": "FPPA + trunk lean + lateral plant contract"},
    {"file": "specs/ira7-biomech-mvp/contracts/15-multi-phone-3d.md", "line_start": 30, "line_end": 110, "reason": "FR-045 minimal mode (audio sync only)"},
    {"file": "specs/ira7-biomech-mvp/data-model.md", "line_start": 700, "line_end": 850, "reason": "Trial extensions + MultiCameraRig + ClipSyncEvent (Phase 3 schema applied to Phase 2 minimal mode)"},
    {"file": "specs/ira7-biomech-mvp/data-model.md", "line_start": 1100, "line_end": 1200, "reason": "Pillar C frontal canonical metric names"},
    {"file": "specs/ira7-biomech-mvp/research.md", "line_start": 1, "line_end": 100, "reason": "research §19.2 frontal topology + §19.10 variant manifest + §19.11 rotation flag (search by section markers)"},
    {"file": "specs/ira7-biomech-mvp/spec.md", "line_start": 1, "line_end": 100, "reason": "FR-037, FR-038, FR-045 specs (search by FR markers)"}
  ]
}
```

Other milestones follow the same pattern; `/task-manifest` should also pull the relevant prd.md user stories (US-019..US-035) and spec.md success criteria (SC-11..SC-25) per the M7-M12 bullet lists in prd.md §8.

---

## 8. /task-manifest Re-Run Plan

The existing tasks.md (57 tasks, 6 phases, 34 FRs mapped) is Phase 1 only. After this plan.md lands and the human gate passes, `/task-manifest` should be re-run with the following posture:

1. **Preserve Phase 1 tasks verbatim.** task-1-1..task-6-19 are approved and locked. Re-running task-manifest must NOT modify them.
2. **Add new phase-task blocks for M7..M12.** Estimated task count per phase: M7 ~12 tasks, M8 ~8 tasks, M9 ~14 tasks, M10 ~12 tasks, M11 ~22 tasks, M12 ~10 tasks. Total ~78 new tasks, bringing tasks.md to ~135 total.
3. **Update tasks.md §Phase Summary** table with the new milestones.
4. **Update tasks.md §Migration Version Owner Contract** with V7..V11.
5. **Re-run snippet_refs verification** for any task that references contracts/ files (the new files 13-17) or data-model.md sections (the new §13–§17).

---

## 9. Plan Quality Self-Check

| Check | Pass |
|---|---|
| Every milestone has FRs + gate (SC reference) + size + affected files | yes |
| Phase sequencing per CONST-INV-008 explicitly enforced | yes (§1 dependency rules) |
| Parallelization opportunities identified | yes (§4) |
| Constitutional enforcement gates listed per phase | yes (§3.5) |
| Migration version allocation documented | yes (§3.2) |
| Build variant strategy documented | yes (§3.1) |
| Pose model asset bundling documented | yes (§3.3) |
| Risks mapped to mitigation in plan | yes (§6) |
| Snippet seeds for /task-manifest provided | yes (§7) |
| /task-manifest re-run posture defined | yes (§8) |

---

**Status:** Draft for /spec human gate. After approval, `/task-manifest` re-runs to extend tasks.md with Phase 2-5 task decomposition; engineering lead approves the extended tasks.md at the standard task-manifest human gate; then `/tasks` produces phase-N.json contracts for each phase as needed.

**End of plan.md.**
