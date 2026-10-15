"""Graves 2013 synthesis network, matching the sjvasquez checkpoint.

Three 400-unit LSTMs, a 10-component attention window over the character
sequence, and a 20-component bivariate mixture for the pen. Weights are the
pretrained checkpoint converted to a NumPy archive. No TensorFlow is required
at generation time, and nothing leaves the machine.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np

from app.handwriting.alphabet import ALPHABET, encode
from app.handwriting.strokes import draw_strokes

log = logging.getLogger(__name__)

LSTM = 400
ATTN = 10
MIX = 20
GMM = 6 * MIX + 1


@dataclass
class Weights:
    lstm1_kernel: np.ndarray
    lstm1_bias: np.ndarray
    lstm2_kernel: np.ndarray
    lstm2_bias: np.ndarray
    lstm3_kernel: np.ndarray
    lstm3_bias: np.ndarray
    attention_weights: np.ndarray
    attention_biases: np.ndarray
    gmm_weights: np.ndarray
    gmm_biases: np.ndarray

    @classmethod
    def load(cls, path: Path) -> "Weights":
        with np.load(path) as archive:
            data = {key: archive[key].astype(np.float32) for key in archive.files}
        weights = cls(**data)
        alphabet = len(ALPHABET)
        expected = {
            "lstm1_kernel": (alphabet + 3 + LSTM, 4 * LSTM),
            "lstm2_kernel": (alphabet + 3 + LSTM + LSTM, 4 * LSTM),
            "lstm3_kernel": (alphabet + 3 + LSTM + LSTM, 4 * LSTM),
            "attention_weights": (alphabet + 3 + LSTM, 3 * ATTN),
            "gmm_weights": (LSTM, GMM),
        }
        for name, shape in expected.items():
            got = getattr(weights, name).shape
            if got != shape:
                raise ValueError(f"{name} has shape {got}, expected {shape}")
        return weights


def _sigmoid(x: np.ndarray) -> np.ndarray:
    return 1.0 / (1.0 + np.exp(-np.clip(x, -40, 40)))


def _softplus(x: np.ndarray) -> np.ndarray:
    return np.log1p(np.exp(np.clip(x, -40, 40)))


def _lstm(x: np.ndarray, h: np.ndarray, c: np.ndarray, kernel: np.ndarray, bias: np.ndarray):
    gates = np.concatenate([x, h]) @ kernel + bias
    i, j, f, o = np.split(gates, 4)
    c_new = c * _sigmoid(f + 1.0) + _sigmoid(i) * np.tanh(j)
    h_new = np.tanh(c_new) * _sigmoid(o)
    return h_new.astype(np.float32), c_new.astype(np.float32)


class _State:
    def __init__(self) -> None:
        self.h1 = np.zeros(LSTM, np.float32)
        self.c1 = np.zeros(LSTM, np.float32)
        self.h2 = np.zeros(LSTM, np.float32)
        self.c2 = np.zeros(LSTM, np.float32)
        self.h3 = np.zeros(LSTM, np.float32)
        self.c3 = np.zeros(LSTM, np.float32)
        self.kappa = np.zeros(ATTN, np.float32)
        self.w = np.zeros(len(ALPHABET), np.float32)
        self.phi = np.zeros(1, np.float32)


class GravesModel:
    def __init__(self, weights: Weights, styles_dir: Path) -> None:
        self.weights = weights
        self.styles_dir = styles_dir

    def style_ids(self) -> list[int]:
        if not self.styles_dir.exists():
            return []
        ids = []
        for path in self.styles_dir.glob("style-*-strokes.npy"):
            piece = path.name.split("-")[1]
            if piece.isdigit():
                ids.append(int(piece))
        return sorted(ids)

    def sample_line(
        self,
        text: str,
        *,
        style_id: int | None,
        bias: float,
        variation: float,
        seed: int | None,
    ) -> np.ndarray:
        cleaned = "".join(ch if ch >= " " else " " for ch in text)[:70]
        if not cleaned.strip():
            return np.zeros((0, 3), np.float32)
        rng = np.random.default_rng(None if seed is None else seed & 0xFFFFFFFF)
        prime, chars = self._prime_sequence(cleaned, style_id)
        encoded = np.asarray(encode(chars), dtype=np.int32)
        one_hot = np.eye(len(ALPHABET), dtype=np.float32)[encoded]
        state = _State()
        state.phi = np.zeros(len(encoded), np.float32)
        primed = prime is not None and len(prime) > 0
        if primed:
            for point in prime:
                state = self._step(state, point.astype(np.float32), one_hot)
            pen = self._sample_pen(state, bias, variation, rng)
        else:
            pen = np.array([0.0, 0.0, 1.0], np.float32)
        limit = 40 * max(1, len(encoded))
        strokes = []
        for step in range(limit):
            pen = np.clip(pen, [-30, -30, 0], [30, 30, 1]).astype(np.float32)
            if primed or step > 0:
                strokes.append(pen.copy())
                focus = int(np.argmax(state.phi)) if state.phi.size else 0
                if focus >= len(encoded) - 1 and pen[2] >= 0.5:
                    break
            state = self._step(state, pen, one_hot)
            pen = self._sample_pen(state, bias, variation, rng)
        if not strokes:
            return np.zeros((0, 3), np.float32)
        return np.stack(strokes).astype(np.float32)

    def render_image(
        self,
        text: str,
        *,
        style_id: int | None,
        bias: float,
        variation: float,
        seed: int | None,
        max_width_px: int,
        max_height_px: int,
        stroke_px: int,
    ):
        offsets = self.sample_line(
            text, style_id=style_id, bias=bias, variation=variation, seed=seed,
        )
        return draw_strokes(
            offsets,
            max_width_px=max_width_px,
            max_height_px=max_height_px,
            stroke_px=stroke_px,
        )

    def _prime_sequence(self, text: str, style_id: int | None) -> tuple[np.ndarray | None, str]:
        if style_id is None:
            return None, text
        strokes_path = self.styles_dir / f"style-{style_id}-strokes.npy"
        chars_path = self.styles_dir / f"style-{style_id}-chars.npy"
        if not strokes_path.exists() or not chars_path.exists():
            log.info("Graves style %s has no primer files; sampling without a primer", style_id)
            return None, text
        strokes = np.load(strokes_path).astype(np.float32)
        if strokes.ndim == 1:
            strokes = strokes.reshape(-1, 3)
        raw = np.load(chars_path, allow_pickle=True)
        item = raw.item() if isinstance(raw, np.ndarray) and raw.shape == () else raw
        if isinstance(item, bytes):
            primer = item.decode("utf-8", "ignore")
        elif isinstance(item, str):
            primer = item
        elif isinstance(raw, np.ndarray) and raw.dtype.kind in {"i", "u"}:
            primer = "".join(
                ALPHABET[int(code)] if 0 <= int(code) < len(ALPHABET) else " "
                for code in raw.reshape(-1)
            )
        else:
            primer = raw.tobytes().decode("utf-8", "ignore")
        primer = "".join(ch for ch in primer if ch >= " " and ch != "\x00")
        return strokes, f"{primer} {text}"

    def _step(self, state: _State, pen: np.ndarray, one_hot: np.ndarray) -> _State:
        weights = self.weights
        nxt = _State()
        nxt.h1, nxt.c1 = _lstm(
            np.concatenate([state.w, pen]), state.h1, state.c1,
            weights.lstm1_kernel, weights.lstm1_bias,
        )
        attn_in = np.concatenate([state.w, pen, nxt.h1])
        params = _softplus(attn_in @ weights.attention_weights + weights.attention_biases)
        alpha, beta, kappa_delta = np.split(params, 3)
        nxt.kappa = state.kappa + kappa_delta / 25.0
        beta = np.maximum(beta, 0.01)
        positions = np.arange(one_hot.shape[0], dtype=np.float32)
        delta = nxt.kappa[:, None] - positions[None, :]
        nxt.phi = np.sum(alpha[:, None] * np.exp(-(delta ** 2) / beta[:, None]), axis=0).astype(np.float32)
        nxt.w = (nxt.phi @ one_hot).astype(np.float32)
        mix = np.concatenate([pen, nxt.h1, nxt.w])
        nxt.h2, nxt.c2 = _lstm(mix, state.h2, state.c2, weights.lstm2_kernel, weights.lstm2_bias)
        nxt.h3, nxt.c3 = _lstm(
            np.concatenate([pen, nxt.h2, nxt.w]), state.h3, state.c3,
            weights.lstm3_kernel, weights.lstm3_bias,
        )
        return nxt

    def _sample_pen(self, state: _State, bias: float, variation: float, rng: np.random.Generator) -> np.ndarray:
        raw = state.h3 @ self.weights.gmm_weights + self.weights.gmm_biases
        pis, sigmas, rhos, mus, es = np.split(raw, [MIX, MIX + 2 * MIX, MIX + 3 * MIX, MIX + 5 * MIX])
        pis = pis * (1.0 + bias)
        sigmas = sigmas - bias
        pis = np.exp(pis - np.max(pis))
        pis = pis / np.maximum(pis.sum(), 1e-8)
        pis = np.where(pis < 0.01, 0.0, pis)
        total = float(pis.sum())
        pis = pis / total if total > 0 else np.full(MIX, 1.0 / MIX, np.float32)
        sigmas = np.clip(np.exp(sigmas), 1e-4, 1e3)
        rhos = np.clip(np.tanh(rhos), -0.999, 0.999)
        end = float(np.clip(1.0 / (1.0 + np.exp(-np.clip(es[0], -40, 40))), 1e-4, 1 - 1e-4))
        if end < 0.01:
            end = 0.0
        index = int(rng.choice(MIX, p=pis))
        mu1, mu2 = mus[index], mus[MIX + index]
        s1, s2 = sigmas[index], sigmas[MIX + index]
        rho = rhos[index]
        z0, z1 = rng.normal(size=2)
        x = mu1 + s1 * z0
        y = mu2 + s2 * (rho * z0 + np.sqrt(max(0.0, 1 - rho * rho)) * z1)
        if variation:
            x += rng.normal(0, variation)
            y += rng.normal(0, variation)
        eos = 1.0 if rng.random() < end else 0.0
        return np.array([x, y, eos], np.float32)
