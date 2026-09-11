"use strict";

// Official zero-code SDK (traces, metrics, logs, auto-instrumentations).
require("@opentelemetry/auto-instrumentations-node/register");

// Express 5 requires `node:http`, which does not trigger the `http` hook.
// Loading `http`/`https` here applies the patch to the shared Node core module.
require("http");
require("https");
