import { api } from "./api";
import { vpc } from "./database";
import { nextAuthSecret } from "./secrets";

const environment: Record<string, $util.Input<string>> = {
  NEXT_PUBLIC_API_URL: $interpolate`http://${api.service}:8000`,
  NEXTAUTH_SECRET: nextAuthSecret.value,
};

export const frontend = new sst.aws.Nextjs("Frontend", {
  path: "frontend",
  vpc,
  link: [api, nextAuthSecret],
  environment,
  dev: {
    command: "pnpm run dev",
    directory: "frontend",
    url: "http://localhost:3000",
  },
});

environment.NEXTAUTH_URL = frontend.url;
