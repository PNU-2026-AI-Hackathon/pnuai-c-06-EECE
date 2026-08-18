import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ command, mode }) => {
  // .env 파일과 VITE_ 로 시작하는 환경변수를 함께 읽는다 (Vercel 대시보드 설정 포함)
  const env = loadEnv(mode, ".", "VITE_");

  /**
   * VITE_API_BASE 가 비면 화면은 목 데이터로 돈다. 개발에는 필요하지만
   * **배포로 나가면 사용자가 가짜 결과를 진짜로 본다.** 문구로는 못 막는다. 빌드를 세운다.
   */
  if (command === "build" && mode === "production" && !env.VITE_API_BASE) {
    throw new Error(
      "VITE_API_BASE 가 비어 있습니다. 이대로 빌드하면 목 데이터가 그대로 배포됩니다.\n" +
        "배포 환경변수에 검사 서버 주소를 넣으세요. 목인 채로 빌드하려면 --mode development."
    );
  }

  return {
    plugins: [react()],
    server: {
      port: 5173,
      // 목표 응답 명세(docs/examples)가 vite 루트 바깥이라 읽기를 열어준다.
      // 사본을 만들지 않기 위한 대가다.
      fs: { allow: [".", "../.."] },
    },
  };
});
