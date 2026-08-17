/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** 백엔드 주소. 비어 있으면 목 데이터로 동작한다 */
  readonly VITE_API_BASE?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
