/// <reference path="./.sst/platform/config.d.ts" />

export default $config({
  app(input) {
    return {
      name: "eluven",
      removal: input?.stage === "production" ? "retain" : "remove",
      protect: input?.stage === "production",
      home: "aws",
    };
  },
  async run() {
    const secrets = await import("./infra/secrets");
    const storage = await import("./infra/storage");
    const queues = await import("./infra/queues");
    const database = await import("./infra/database");
    const api = await import("./infra/api");
    const frontend = await import("./infra/frontend");

    return {
      apiService: api.api.service,
      frontendUrl: frontend.frontend.url,
    };
  },
});
