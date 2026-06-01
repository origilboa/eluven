import type { DefaultSession } from "next-auth";

import type { UserResponse } from "@/lib/types/api";

declare module "next-auth" {
  interface Session extends DefaultSession {
    accessToken: string;
    user: UserResponse;
  }

  interface User {
    accessToken: string;
    profile: UserResponse;
  }
}

declare module "next-auth/jwt" {
  interface JWT {
    accessToken?: string;
    profile?: UserResponse;
  }
}

export {};
