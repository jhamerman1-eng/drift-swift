FROM node:20-alpine
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install --production || npm install
COPY tsconfig.json ./
COPY src ./src
RUN npx tsc -p tsconfig.json
EXPOSE 8787
CMD ["node", "dist/index.js"]
