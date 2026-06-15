import assert from "node:assert/strict";
import test from "node:test";

import {
  compactToolResult,
  mergeKernelMirrorEventsIntoHistory,
  trimWorkingMessagesForProvider
} from "../../client_frontend/pipeline_agent/context_policy.js";
import { mirrorEvent, recoveryOption } from "./pipeline-agent-test-fixtures.js";

test("kernel mirror entries are preserved as internal history and converted to system context for provider calls", () => {
  const history = mergeKernelMirrorEventsIntoHistory([], [
    mirrorEvent({
      mirror_event_id: "mev_1001",
      recovery_event_id: "rev_1001",
      allowed_agent_tools: ["kernel_open_recovery_dialog"],
      recovery_options: [
        recoveryOption({
          recovery_id: "rcv_1001",
          recovery_event_id: "rev_1001",
          agent_tool: "kernel_open_recovery_dialog"
        })
      ]
    })
  ]);
  const providerMessages = trimWorkingMessagesForProvider(
    [
      { role: "system", content: "system prompt" },
      ...history,
      { role: "user", content: "what happened?" }
    ],
    [],
    100_000
  );

  assert.equal(history[0].role, "kernel");
  assert.equal(providerMessages[1].role, "system");
  assert.match(providerMessages[1].content, /Kernel mirror event\. This is Kernel state, not a user message\./);
  assert.match(providerMessages[1].content, /kernel_open_recovery_dialog/);
});

test("kernel mirror history deduplicates mirror_event_id while keeping the latest payload", () => {
  const history = mergeKernelMirrorEventsIntoHistory(
    mergeKernelMirrorEventsIntoHistory([], [mirrorEvent({ mirror_event_id: "mev_2001", user_visible_summary: "Older" })]),
    [mirrorEvent({ mirror_event_id: "mev_2001", user_visible_summary: "Newer" })]
  );

  assert.equal(history.length, 1);
  assert.equal(history[0].kernel_mirror_event.user_visible_summary, "Newer");
});

test("large mirror payloads are compacted without dropping recovery options and allowed agent tools", () => {
  const content = compactToolResult("kernel_status", {
    schema_version: "semantic_control_kernel.mcp_response.v1",
    status: "blocked",
    tool_name: "kernel_status",
    effect: "none",
    user_visible_summary: "Kernel blocked.",
    mirror_event: mirrorEvent({
      mirror_event_id: "mev_3001",
      user_visible_cause: "x".repeat(12_000),
      recovery_event_id: "rev_3001",
      recovery_options: [
        recoveryOption({
          recovery_id: "rec_1",
          recovery_event_id: "rev_3001",
          label: "Retry",
          description: "Retry now.",
          agent_tool: "kernel_retry_recoverable_workflow"
        }),
        recoveryOption({
          recovery_id: "rec_2",
          recovery_event_id: "rev_3001",
          label: "Open support bundle",
          description: "Open the Kernel support bundle.",
          agent_tool: "kernel_open_support_bundle",
          support_bundle_ref: { support_bundle_id: "sb_3001" }
        })
      ],
      allowed_agent_tools: ["kernel_retry_recoverable_workflow", "kernel_open_support_bundle"]
    })
  });

  assert.match(content, /kernel_retry_recoverable_workflow/);
  assert.match(content, /kernel_open_support_bundle/);
  assert.match(content, /rec_1/);
  assert.ok(content.length < 24_500);
});
