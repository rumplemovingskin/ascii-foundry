from __future__ import annotations

from ascii_foundry.core.ffmpeg_tools import find_ffmpeg
from ascii_foundry.core.settings import VideoSettings
from ascii_foundry.core.video_pipeline import (
    _parse_fps,
    choose_sample_frame_number,
    choose_sample_timestamp,
    mux_audio_if_possible,
    rebuild_video,
    video_frame_count,
)


def test_parse_fps() -> None:
    assert _parse_fps("30000/1001") == 30000 / 1001
    assert _parse_fps("24") == 24
    assert _parse_fps("0/0") is None
    assert _parse_fps("not-fps") is None


def test_choose_sample_timestamp_is_seeded(monkeypatch) -> None:
    monkeypatch.setattr("ascii_foundry.core.video_pipeline.video_duration_seconds", lambda path, ffprobe_path=None: 10.0)

    first = choose_sample_timestamp("input.mp4", random_frame=False, seed=123)
    second = choose_sample_timestamp("input.mp4", random_frame=False, seed=123)
    middle = choose_sample_timestamp("input.mp4", random_frame=False, seed=123)
    random_seeded = choose_sample_timestamp("input.mp4", random_frame=True, seed=123)

    assert first == second
    assert middle == first
    assert 0.0 <= random_seeded <= 9.0


def test_choose_sample_timestamp_defaults_to_middle(monkeypatch) -> None:
    monkeypatch.setattr("ascii_foundry.core.video_pipeline.video_duration_seconds", lambda path, ffprobe_path=None: 10.0)

    assert choose_sample_timestamp("input.mp4", random_frame=False, seed=None) == 5.0


def test_choose_sample_frame_number_defaults_to_first_frame(monkeypatch) -> None:
    monkeypatch.setattr("ascii_foundry.core.video_pipeline.video_frame_count", lambda path, ffprobe_path=None: 42)

    assert choose_sample_frame_number("input.mp4", random_frame=False, frame_number=None) == (1, 42)


def test_choose_sample_frame_number_reports_total_when_too_high(monkeypatch) -> None:
    monkeypatch.setattr("ascii_foundry.core.video_pipeline.video_frame_count", lambda path, ffprobe_path=None: 42)

    try:
        choose_sample_frame_number("input.mp4", random_frame=False, frame_number=99)
    except ValueError as exc:
        assert "Frame 99" in str(exc)
        assert "Total frames: 42" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_video_frame_count_uses_nb_frames(monkeypatch) -> None:
    monkeypatch.setattr(
        "ascii_foundry.core.video_pipeline.ffprobe_metadata",
        lambda path, ffprobe_path=None: {
            "streams": [{"codec_type": "video", "nb_frames": "123"}],
            "format": {},
        },
    )

    assert video_frame_count("input.mp4") == 123


def test_video_frame_count_falls_back_to_duration_times_fps(monkeypatch) -> None:
    monkeypatch.setattr(
        "ascii_foundry.core.video_pipeline.ffprobe_metadata",
        lambda path, ffprobe_path=None: {
            "streams": [{"codec_type": "video", "duration": "10", "avg_frame_rate": "30000/1001"}],
            "format": {},
        },
    )

    assert video_frame_count("input.mp4") == 300


def test_rebuild_video_command_shape(monkeypatch, tmp_path) -> None:
    commands = []

    def fake_run(command, progress_callback=None):
        commands.append(command)

    monkeypatch.setattr("ascii_foundry.core.video_pipeline.run_command", fake_run)
    rebuild_video(tmp_path, tmp_path / "out.mp4", 30, VideoSettings(crf=22, preset="fast"))

    command = commands[0]
    assert "-framerate" in command
    assert "30" in command
    assert "-vf" in command
    assert "pad=ceil(iw/2)*2:ceil(ih/2)*2" in command
    assert "-crf" in command
    assert "22" in command
    assert "-preset" in command
    assert str(tmp_path / "out.mp4") == command[-1]


def test_rebuild_video_uses_bitrate_when_provided(monkeypatch, tmp_path) -> None:
    commands = []

    def fake_run(command, progress_callback=None):
        commands.append(command)

    monkeypatch.setattr("ascii_foundry.core.video_pipeline.run_command", fake_run)
    rebuild_video(tmp_path, tmp_path / "out.webm", 24, VideoSettings(codec="libvpx-vp9", bitrate="6M"))

    command = commands[0]
    assert "-b:v" in command
    assert "6M" in command
    assert "-preset" not in command


def test_rebuild_video_has_gif_command(monkeypatch, tmp_path) -> None:
    commands = []

    def fake_run(command, progress_callback=None):
        commands.append(command)

    monkeypatch.setattr("ascii_foundry.core.video_pipeline.run_command", fake_run)
    rebuild_video(tmp_path, tmp_path / "out.gif", 12, VideoSettings(output_format="gif", codec="gif"))

    command = commands[0]
    assert "palettegen" in " ".join(command)
    assert "-c:v" not in command
    assert str(tmp_path / "out.gif") == command[-1]


def test_mux_audio_if_possible_writes_to_temp_then_replaces(monkeypatch, tmp_path) -> None:
    silent = tmp_path / "silent.mp4"
    output = tmp_path / "out.mp4"
    silent.write_text("silent", encoding="utf-8")
    output.write_text("old", encoding="utf-8")

    def fake_run(command, progress_callback=None):
        temp_output = command[-1]
        assert temp_output != str(output)
        assert str(silent) in command
        tmp_path.joinpath(".out.with_audio.mp4").write_text("muxed", encoding="utf-8")

    monkeypatch.setattr("ascii_foundry.core.video_pipeline.run_command", fake_run)

    assert mux_audio_if_possible("input.mp4", silent, output)
    assert output.read_text(encoding="utf-8") == "muxed"


def test_find_ffmpeg_prefers_bundled_binary(monkeypatch, tmp_path) -> None:
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    ffmpeg = bin_dir / "ffmpeg.exe"
    ffprobe = bin_dir / "ffprobe.exe"
    ffmpeg.write_text("", encoding="utf-8")
    ffprobe.write_text("", encoding="utf-8")

    monkeypatch.setattr("ascii_foundry.core.ffmpeg_tools.sys.frozen", True, raising=False)
    monkeypatch.setattr("ascii_foundry.core.ffmpeg_tools.sys.platform", "win32")
    monkeypatch.setattr("ascii_foundry.core.ffmpeg_tools.sys.executable", str(tmp_path / "ASCII Foundry.exe"))
    monkeypatch.setenv("PATH", "")

    availability = find_ffmpeg()

    assert availability.ffmpeg_path == str(ffmpeg)
    assert availability.ffprobe_path == str(ffprobe)
