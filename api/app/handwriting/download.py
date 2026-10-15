"""Download the sjvasquez Graves checkpoint and export a NumPy weight file.

Generation does not use TensorFlow. This converter reads the checkpoint bundle directly.

    cd api
    python -m app.handwriting.download
"""
from __future__ import annotations

import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2] / "data" / "graves"
CHECKPOINT = "https://raw.githubusercontent.com/sjvasquez/handwriting-synthesis/master/checkpoints"
STYLES = "https://raw.githubusercontent.com/sjvasquez/handwriting-synthesis/master/styles"
FILES = [
    "checkpoint",
    "model-17900.index",
    "model-17900.data-00000-of-00001",
]
KEYS = {
    "rnn/LSTMAttentionCell/lstm_cell/kernel": "lstm1_kernel",
    "rnn/LSTMAttentionCell/lstm_cell/bias": "lstm1_bias",
    "rnn/LSTMAttentionCell/lstm_cell_1/kernel": "lstm2_kernel",
    "rnn/LSTMAttentionCell/lstm_cell_1/bias": "lstm2_bias",
    "rnn/LSTMAttentionCell/lstm_cell_2/kernel": "lstm3_kernel",
    "rnn/LSTMAttentionCell/lstm_cell_2/bias": "lstm3_bias",
    "rnn/LSTMAttentionCell/attention/weights": "attention_weights",
    "rnn/LSTMAttentionCell/attention/biases": "attention_biases",
    "rnn/gmm/weights": "gmm_weights",
    "rnn/gmm/biases": "gmm_biases",
}


def _fetch(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists() and dest.stat().st_size > 0:
        print(f"exists {dest}", flush=True)
        return
    print(f"download {url}", flush=True)
    request = urllib.request.Request(url, headers={"User-Agent": "handscript"})
    with urllib.request.urlopen(request, timeout=120) as response, dest.open("wb") as handle:
        while True:
            chunk = response.read(1024 * 256)
            if not chunk:
                break
            handle.write(chunk)


def _varint(buf: bytes, index: int) -> tuple[int, int]:
    result = 0
    shift = 0
    while True:
        byte = buf[index]
        index += 1
        result |= (byte & 0x7F) << shift
        if byte < 128:
            return result, index
        shift += 7


def _decode_block(block: bytes) -> list[tuple[bytes, bytes]]:
    restarts = int.from_bytes(block[-4:], "little")
    end = len(block) - 4 - restarts * 4
    index = 0
    key = b""
    entries: list[tuple[bytes, bytes]] = []
    while index < end:
        shared, index = _varint(block, index)
        unshared, index = _varint(block, index)
        value_len, index = _varint(block, index)
        key = key[:shared] + block[index:index + unshared]
        index += unshared
        entries.append((key, block[index:index + value_len]))
        index += value_len
    return entries


def _proto_fields(buf: bytes) -> dict[int, list]:
    index = 0
    fields: dict[int, list] = {}
    while index < len(buf):
        key, index = _varint(buf, index)
        field, wire = key >> 3, key & 7
        if wire == 0:
            value, index = _varint(buf, index)
        elif wire == 2:
            length, index = _varint(buf, index)
            value = buf[index:index + length]
            index += length
        elif wire == 5:
            value = int.from_bytes(buf[index:index + 4], "little")
            index += 4
        else:
            raise ValueError(f"unsupported checkpoint field wire type {wire}")
        fields.setdefault(field, []).append(value)
    return fields


def _shape(raw: bytes) -> tuple[int, ...]:
    dims = []
    for dim in _proto_fields(raw).get(2, []):
        size = _proto_fields(dim).get(1, [1])[0]
        dims.append(int(size))
    return tuple(dims)


def export_weights(checkpoint_prefix: Path, dest: Path) -> None:
    """Read the TensorFlow bundle and store the inference tensors as ``.npz``."""
    import numpy as np

    index = Path(str(checkpoint_prefix) + ".index").read_bytes()
    data_path = Path(str(checkpoint_prefix) + ".data-00000-of-00001")
    footer = index[-48:-8]
    _, _, cursor = _handle(footer, 0)
    block_offset, block_size, _cursor = _handle(footer, cursor)
    block = index[block_offset:block_offset + block_size]
    handle_key, handle_value = _decode_block(block)[0]
    del handle_key
    data_offset, data_size, _cursor = _handle(handle_value, 0)
    entries = dict(_decode_block(index[data_offset:data_offset + data_size]))
    blob = data_path.read_bytes()
    arrays = {}
    for source, name in KEYS.items():
        fields = _proto_fields(entries[source.encode()])
        offset = int(fields[4][0])
        size = int(fields[5][0])
        shape = _shape(fields[2][0])
        arrays[name] = np.frombuffer(blob[offset:offset + size], dtype="<f4").reshape(shape).copy()
    dest.parent.mkdir(parents=True, exist_ok=True)
    np.savez(dest, **arrays)
    for name, value in arrays.items():
        print(f"{name} {value.shape}", flush=True)
    print(f"wrote {dest}", flush=True)


def _handle(buf: bytes, index: int) -> tuple[int, int, int]:
    offset, index = _varint(buf, index)
    size, index = _varint(buf, index)
    return offset, size, index


def main() -> None:
    checkpoint_dir = ROOT / "checkpoints"
    for name in FILES:
        _fetch(f"{CHECKPOINT}/{name}", checkpoint_dir / name)
    styles = ROOT / "styles"
    for index in range(21):
        for kind in ("strokes", "chars"):
            filename = f"style-{index}-{kind}.npy"
            try:
                _fetch(f"{STYLES}/{filename}", styles / filename)
            except Exception as exc:
                print(f"skip {filename}: {exc}")
    export_weights(checkpoint_dir / "model-17900", ROOT / "weights.npz")


if __name__ == "__main__":
    main()
