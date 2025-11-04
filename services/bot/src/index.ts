import { Hono } from "hono";
import { Bindings } from "./configuration";

const app = new Hono<{ Bindings: Bindings }>();

app.get("/", (c) => c.text("Yarumotors is Running."));

app.all("*", (c) => c.text("Not Found.", { status: 404 }));

export default app;
