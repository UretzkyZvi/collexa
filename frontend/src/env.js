/* eslint-disable no-undef */
import { createEnv } from "@t3-oss/env-nextjs";
import { z } from "zod";

export const env = createEnv({
  // Server-only env
  server: {
    NODE_ENV: z.enum(["development", "test", "production"]).default("development"),
    STACK_SECRET_SERVER_KEY: z.string(),
  },
  // Client-exposed env (must be prefixed NEXT_PUBLIC_)
  client: {
    NEXT_PUBLIC_STACK_PROJECT_ID: z.string(),
    NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY: z.string(),
    NEXT_PUBLIC_API_BASE_URL: z.string().url().optional(),
  },
  // Bind process.env
  runtimeEnv: {
    NODE_ENV: process.env.NODE_ENV,
    STACK_SECRET_SERVER_KEY: process.env.STACK_SECRET_SERVER_KEY,
    NEXT_PUBLIC_STACK_PROJECT_ID: process.env.NEXT_PUBLIC_STACK_PROJECT_ID,
    NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY: process.env.NEXT_PUBLIC_STACK_PUBLISHABLE_CLIENT_KEY,
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
  },
  skipValidation: !!process.env.SKIP_ENV_VALIDATION,
  emptyStringAsUndefined: true,
});
