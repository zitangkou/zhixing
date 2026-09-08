# Taro 原生 binding 需 glibc（package-lock 为 linux-x64-gnu），勿用 alpine
FROM node:20-bookworm-slim AS h5-build
WORKDIR /app
# 国内服务器构建：npm 走 npmmirror，避免直连 npmjs.org 超时
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
# .npmrc 含 legacy-peer-deps，与本地 npm install 行为一致
COPY package.json package-lock.json .npmrc ./
RUN npm ci --legacy-peer-deps
COPY config ./config
COPY src ./src
COPY tsconfig.json babel.config.js project.config.json ./
COPY types ./types
ENV NODE_ENV=production
ENV TARO_APP_API_URL=
RUN npm run build:h5

# 两个垂直产品共享根依赖，但各自独立编译和产出。
COPY apps/shenlun-app ./apps/shenlun-app
COPY apps/theory-app ./apps/theory-app
RUN cd apps/shenlun-app \
    && TARO_APP_API_URL= TARO_APP_PUBLIC_PATH=/shenlun/ npm run build:h5
RUN cd apps/theory-app \
    && TARO_APP_API_URL= TARO_APP_PUBLIC_PATH=/theory/ npm run build:h5

FROM node:20-alpine AS admin-build
ENV NPM_CONFIG_REGISTRY=https://registry.npmmirror.com
WORKDIR /app/server/admin-web
COPY server/admin-web/package.json server/admin-web/package-lock.json ./
RUN npm ci
COPY server/admin-web .
RUN npm run build

FROM python:3.12-slim
ENV TZ=Asia/Shanghai
RUN sed -i 's|deb.debian.org|mirrors.aliyun.com|g' /etc/apt/sources.list.d/debian.sources /etc/apt/sources.list 2>/dev/null || true \
    && apt-get update \
    && apt-get install -y --no-install-recommends nginx tzdata \
    && ln -snf /usr/share/zoneinfo/$TZ /etc/localtime \
    && echo $TZ > /etc/timezone \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app/server
COPY server/requirements.txt .
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt

COPY server .
COPY --from=admin-build /app/server/admin-dist ./admin-dist
COPY --from=h5-build /app/dist /usr/share/nginx/html
COPY --from=h5-build /app/apps/shenlun-app/dist /usr/share/nginx/html/shenlun
COPY --from=h5-build /app/apps/theory-app/dist /usr/share/nginx/html/theory
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY docker/start.sh /start.sh
RUN chmod +x /start.sh \
    && mkdir -p data \
    && rm -f /etc/nginx/sites-enabled/default

EXPOSE 80
CMD ["/start.sh"]
