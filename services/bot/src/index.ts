import { Hono } from "hono";
import { Bindings } from "./types/configuration";
import { verifyKey } from "discord-interactions";
import {
  APIInteraction,
  InteractionResponseType,
  InteractionType,
} from "discord-api-types/v10";
import * as commands from "./commands";

const app = new Hono<{ Bindings: Bindings }>();

app.get("/", (c) => c.text("Yarumotors is Running."));

app.post("/interactions", async (c) => {
  const signature = c.req.header("x-signature-ed25519");
  const timestamp = c.req.header("x-signature-timestamp");
  const body = await c.req.text();

  const isValid = await verifyKey(
    body,
    signature!,
    timestamp!,
    c.env.DISCORD_PUBLIC_KEY,
  );
  if (!isValid) return c.text("Invalid signature.", 401);

  const interaction = JSON.parse(body) as APIInteraction;

  switch (interaction.type) {
    case InteractionType.Ping:
      return c.json({ type: InteractionResponseType.Pong });
    case InteractionType.ApplicationCommand: {
      switch (interaction.data.name.toLowerCase()) {
        case commands.PING_COMMAND.name.toLowerCase(): {
          const DISCORD_SNOWFLAKE = 4194304;
          const DISCORD_EPOCH_TIMESTAMP = 1420070400000;

          const latency =
            Date.now() -
            Math.round(
              Number(interaction.id) / DISCORD_SNOWFLAKE +
                DISCORD_EPOCH_TIMESTAMP,
            );

          return c.json({
            type: InteractionResponseType.ChannelMessageWithSource,
            data: {
              embeds: [
                {
                  title: "Pong!",
                  description: `Bot latency: **${latency} ms** (rounded)`,
                  color: 0x5865f2, // Discord blurple
                  footer: {
                    text: "Yarumotors Bot",
                  },
                  timestamp: new Date().toISOString(),
                },
              ],
            },
          });
        }
      }
      break;
    }

    default:
      return c.json({ error: "Unknown Type" }, { status: 400 });
  }

  console.error("Unknown Type");
  return c.json({ error: "Unknown Type" }, { status: 400 });
});

app.all("*", (c) => c.text("Not Found.", { status: 404 }));

export default app;
