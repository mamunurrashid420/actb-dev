import "@testing-library/jest-dom";
import "whatwg-fetch";

// Ensure Web Fetch API globals exist in JSDOM environment without using `any`
interface GlobalFetchLike {
  Response?: typeof Response;
  Headers?: typeof Headers;
  Request?: typeof Request;
}

const g = globalThis as GlobalFetchLike & typeof globalThis;

if (typeof g.Response === "undefined" && typeof window !== "undefined") {
  g.Response = window.Response as typeof Response;
}
if (typeof g.Headers === "undefined" && typeof window !== "undefined") {
  g.Headers = window.Headers as typeof Headers;
}
if (typeof g.Request === "undefined" && typeof window !== "undefined") {
  g.Request = window.Request as typeof Request;
}
