import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 목표 응답 명세(docs/examples)가 vite 루트 바깥이라 읽기를 열어준다.
    // 사본을 만들지 않기 위한 대가다.
    fs: { allow: [".", "../.."] },
  },
});
