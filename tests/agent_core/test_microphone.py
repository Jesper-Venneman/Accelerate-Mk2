"""Tests for kathrena.agent_core.push_to_talk.microphone - the module's one hardware touchpoint."""

from __future__ import annotations

import numpy as np
import pytest

from kathrena.agent_core.push_to_talk.microphone import sanitize


def test_sanitize_clips_out_of_range_values():
    samples = np.array([0.5, -0.5, 2.0, -2.0], dtype=np.float32)

    cleaned = sanitize(samples, sample_rate=16000)

    assert np.array_equal(cleaned, np.array([0.5, -0.5, 1.0, -1.0], dtype=np.float32))


def test_sanitize_replaces_nan_and_inf_with_zero():
    samples = np.array([0.1, np.nan, np.inf, -np.inf], dtype=np.float32)

    cleaned = sanitize(samples, sample_rate=16000)

    assert np.array_equal(cleaned, np.array([0.1, 0.0, 0.0, 0.0], dtype=np.float32))


def test_sanitize_leaves_valid_audio_unchanged():
    samples = np.array([0.1, -0.2, 0.3], dtype=np.float32)

    cleaned = sanitize(samples, sample_rate=16000)

    assert np.array_equal(cleaned, samples)


def test_sanitize_never_overflows_on_garbage_input():
    """Regression test: a corrupted buffer (huge/NaN values) used to overflow computing RMS."""
    garbage = np.array([1e30, -1e30, np.nan], dtype=np.float32)

    cleaned = sanitize(garbage, sample_rate=16000)
    energy = float(np.sqrt(np.mean(np.square(cleaned))))

    assert np.isfinite(energy)
    assert energy == pytest.approx(np.sqrt(2 / 3))
