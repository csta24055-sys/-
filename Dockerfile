# WLC Studio public demo (research / trial version; fictional emission factors; not for formal calculations).
# Every visitor shares the same data, kept in /tmp and wiped on restart. Uploads and address lookups are off.
FROM python:3.13-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 WLCSTUDIO_PUBLIC_DEMO=1 WLCSTUDIO_OFFLINE=1
WORKDIR /srv
COPY whole-life-carbon-jcat-study/09_APPROX_STUDY whole-life-carbon-jcat-study/09_APPROX_STUDY
COPY whole-life-carbon-jcat-study/10_TRANSFORM_STUDY whole-life-carbon-jcat-study/10_TRANSFORM_STUDY
COPY whole-life-carbon-jcat-study/12_APP_BASE whole-life-carbon-jcat-study/12_APP_BASE
COPY whole-life-carbon-jcat-study/23_WLC_STUDIO_APP whole-life-carbon-jcat-study/23_WLC_STUDIO_APP
WORKDIR /srv/whole-life-carbon-jcat-study/23_WLC_STUDIO_APP
EXPOSE 10000
CMD ["sh", "-c", "python3 -B -m wlcstudio --var /tmp/wlc-var serve --host 0.0.0.0 --port ${PORT:-10000}"]
