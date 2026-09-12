FROM python:3.12-slim
ARG PIP_INDEX_URL=https://pypi.org/simple
RUN --mount=type=cache,target=/root/.cache/pip pip install --index-url ${PIP_INDEX_URL} numpy pandas scipy statsmodels matplotlib seaborn scikit-learn openpyxl pyarrow pillow
COPY runner.py /opt/research/runner.py
RUN pip freeze > /opt/research/packages.txt
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MPLBACKEND=Agg MPLCONFIGDIR=/tmp/matplotlib HOME=/tmp OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
USER 65534:65534
WORKDIR /outputs
ENTRYPOINT ["python", "-I", "/opt/research/runner.py"]
