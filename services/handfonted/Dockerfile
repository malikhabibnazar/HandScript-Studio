FROM python:3.11-slim-bookworm

RUN apt-get update && apt-get install -y --no-install-recommends \
        git \
        libglib2.0-0 \
        libgl1 \
        libgomp1 \
        libsm6 \
        libxext6 \
        libxrender1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/handfonted

# CPU wheels only. The CUDA builds are large and this service does not need a GPU.
RUN pip install --no-cache-dir \
        torch==2.5.1 torchvision==0.20.1 \
        --index-url https://download.pytorch.org/whl/cpu

COPY requirements.txt .
ENV PIP_DEFAULT_TIMEOUT=300
# Separate layers so a stalled download does not throw away packages that already installed.
RUN pip install --no-cache-dir --timeout 300 --retries 20 \
        numpy==2.2.6 pillow==11.1.0 fonttools==4.62.1 \
        fastapi==0.115.6 "uvicorn==0.34.0" python-multipart==0.0.20
RUN pip install --no-cache-dir --timeout 300 --retries 20 opencv-contrib-python==4.10.0.84
# Large wheels on a slow link sometimes arrive with a bad hash. Retry the
# install instead of failing the whole image.
RUN set -eu; ok=0; \
    for i in 1 2 3 4 5; do \
      if pip install --no-cache-dir --timeout 300 --retries 5 scipy==1.15.2; then ok=1; break; fi; \
      echo "scipy install attempt $i failed"; sleep 8; \
    done; \
    test "$ok" = 1
RUN set -eu; ok=0; \
    for i in 1 2 3 4 5; do \
      if pip install --no-cache-dir --timeout 300 --retries 5 scikit-image==0.25.2; then ok=1; break; fi; \
      echo "scikit-image install attempt $i failed"; sleep 8; \
    done; \
    test "$ok" = 1
RUN set -eu; ok=0; \
    for i in 1 2 3 4 5; do \
      if pip install --no-cache-dir --timeout 300 --retries 5 paddlepaddle==3.2.2; then ok=1; break; fi; \
      echo "paddlepaddle install attempt $i failed"; sleep 8; \
    done; \
    test "$ok" = 1
RUN set -eu; ok=0; \
    for i in 1 2 3 4 5; do \
      if pip install --no-cache-dir --timeout 300 --retries 5 paddleocr==3.4.0 \
        && python -c "import torch; print('torch', torch.__version__)"; then ok=1; break; fi; \
      echo "paddleocr install attempt $i failed"; sleep 8; \
    done; \
    test "$ok" = 1

RUN set -eu; ok=0; \
    for i in 1 2 3 4 5; do \
      if git clone --depth 1 https://github.com/reshamgaire/HandFonted.git /opt/handfonted/HandFonted; then ok=1; break; fi; \
      rm -rf /opt/handfonted/HandFonted; \
      echo "HandFonted clone attempt $i failed"; sleep 8; \
    done; \
    test "$ok" = 1

COPY server.py .
COPY weights/resinception_byclass62.pth /opt/handfonted/weights/resinception_byclass62.pth

ENV PYTHONPATH=/opt/handfonted/HandFonted \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    FLAGS_use_mkldnn=0 \
    OMP_NUM_THREADS=1

EXPOSE 8010
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010"]
