# Simple dev Dockerfile for the Swift sidecar
FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* pnpm-lock.yaml* yarn.lock* .npmrc* ./ 2>/dev/null || true
RUN npm i --no-audit --no-fund
COPY tsconfig.json ./
COPY src ./src
EXPOSE 8787
CMD ["npm","run","dev"]
