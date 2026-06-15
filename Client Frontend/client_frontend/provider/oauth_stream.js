export function decodeSseEvents(rawText) {
  const events = [];
  let eventName = "message";
  let dataLines = [];
  const flush = () => {
    if (!dataLines.length) return;
    events.push({ event: eventName, data: JSON.parse(dataLines.join("\n")) });
    eventName = "message";
    dataLines = [];
  };
  for (const line of String(rawText || "").split(/\r?\n/)) {
    if (!line.trim()) {
      flush();
      continue;
    }
    if (line.startsWith(":")) continue;
    if (line.startsWith("event:")) {
      eventName = line.slice(6).trim() || "message";
      continue;
    }
    if (line.startsWith("data:")) {
      dataLines.push(line.slice(5).trimStart());
    }
  }
  flush();
  return events;
}

export function buildAssistantMessage(events) {
  const completed = [...events].reverse().find((event) => event.event === "response.completed")?.data?.response || {};
  const textEvent = [...events].reverse().find((event) => event.event === "response.output_text.done");
  const output = Array.isArray(completed.output) ? completed.output : [];
  const content = textEvent?.data?.text
    || output.flatMap((item) => Array.isArray(item?.content) ? item.content : []).find((part) => part?.type === "output_text")?.text
    || events.filter((event) => event.event === "response.output_text.delta").map((event) => event.data?.delta || "").join("")
    || "";
  const tool_calls = mergeToolCalls(
    output
      .filter((item) => item?.type === "function_call" && item?.name)
      .map(toChatToolCall),
    streamFunctionCalls(events)
  );
  return { role: "assistant", content, ...(tool_calls.length ? { tool_calls } : {}) };
}

function streamFunctionCalls(events) {
  const argumentsByItemId = new Map();
  const argumentDeltasByItemId = new Map();
  for (const event of events) {
    const itemId = String(event?.data?.item_id || "").trim();
    if (!itemId) continue;
    if (event.event === "response.function_call_arguments.done") {
      argumentsByItemId.set(itemId, String(event.data?.arguments || ""));
    } else if (event.event === "response.function_call_arguments.delta") {
      argumentDeltasByItemId.set(itemId, `${argumentDeltasByItemId.get(itemId) || ""}${event.data?.delta || ""}`);
    }
  }
  return events
    .filter((event) => event.event === "response.output_item.done")
    .map((event) => {
      const item = event?.data?.item;
      if (item?.type !== "function_call" || !item?.name) return null;
      const itemId = String(item.id || "").trim();
      return toChatToolCall({
        ...item,
        arguments: typeof item.arguments === "string" && item.arguments
          ? item.arguments
          : argumentsByItemId.get(itemId) || argumentDeltasByItemId.get(itemId) || ""
      });
    })
    .filter(Boolean);
}

function toChatToolCall(item, index = 0) {
  return {
    id: String(item.call_id || item.id || `tool_${index + 1}`),
    type: "function",
    function: {
      name: String(item.name || ""),
      arguments: typeof item.arguments === "string" ? item.arguments : JSON.stringify(item.arguments || {})
    }
  };
}

function mergeToolCalls(...groups) {
  const result = [];
  const seen = new Set();
  for (const toolCall of groups.flat()) {
    if (!toolCall?.function?.name) continue;
    const key = String(toolCall.id || `${toolCall.function.name}:${toolCall.function.arguments || ""}`);
    if (seen.has(key)) continue;
    seen.add(key);
    result.push(toolCall);
  }
  return result;
}
