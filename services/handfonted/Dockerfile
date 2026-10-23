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
RUN pip install --no-cache-dir --timeout 300 --retries 20 scikit-image==0.25.2 scipy==1.15.2
RUN pip install --no-cache-dir --timeout 300 --retries 20 paddlepaddle==3.2.2
RUN pip install --no-cache-dir --timeout 300 --retries 20 paddleocr==3.4.0 \
    && python -c "import torch; print('torch', torch.__version__)"

RUN git clone --depth 1 https://github.com/reshamgaire/HandFonted.git /opt/handfonted/HandFonted

COPY server.py .
COPY weights/resinception_byclass62.pth /opt/handfonted/weights/resinception_byclass62.pth

ENV PYTHONPATH=/opt/handfonted/HandFonted \
    PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK=True \
    FLAGS_use_mkldnn=0 \
    OMP_NUM_THREADS=1

EXPOSE 8010
CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "8010"]
