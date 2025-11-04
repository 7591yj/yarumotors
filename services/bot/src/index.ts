import { Hono } from "hono";
import { Bindings } from "./types/configuration";
import { InteractionResponseFlags, verifyKey } from "discord-interactions";
import {
  APIInteraction,
  APIMessageComponentInteraction,
  APIMessageStringSelectInteractionData,
  ComponentType,
  InteractionResponseType,
  InteractionType,
} from "discord-api-types/v10";
import * as commands from "./commands";
import {
  DISCORD_SNOWFLAKE,
  DISCORD_EPOCH_TIMESTAMP,
  COLOR_DISCORD_PURPLE,
} from "./utils/consts";
import { getGps } from "./utils/getGps";

const app = new Hono<{ Bindings: Bindings }>();

//--------------------------------------------------------------
// Health check
//--------------------------------------------------------------
app.get("/", (c) => c.text("Yarumotors is Running."));

//--------------------------------------------------------------
// Interactions endpoint
//--------------------------------------------------------------
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
    // Handles Discord’s initial verification ping
    case InteractionType.Ping:
      return c.json({ type: InteractionResponseType.Pong });

    // Handles all user-issued application commands (e.g. /ping)
    case InteractionType.ApplicationCommand: {
      switch (interaction.data.name.toLowerCase()) {
        // /ping
        case commands.PING_COMMAND.name.toLowerCase(): {
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
                  color: COLOR_DISCORD_PURPLE,
                  footer: {
                    text: "Yarumotors Bot",
                  },
                  timestamp: new Date().toISOString(),
                },
              ],
            },
          });
        }
        // /session
        case commands.GET_SESSION_COMMAND.name.toLocaleLowerCase(): {
          const years = Array.from({ length: 7 }, (_, i) => 2019 + i);
          return c.json({
            type: InteractionResponseType.ChannelMessageWithSource,
            data: {
              flags: InteractionResponseFlags.EPHEMERAL,
              content: "Select a year:",
              components: [
                {
                  type: 1,
                  components: [
                    {
                      type: ComponentType.StringSelect,
                      custom_id: "select_year",
                      options: years.map((y) => ({
                        label: y.toString(),
                        value: y.toString(),
                      })),
                    },
                  ],
                },
              ],
            },
          });
        }
      }
      break;
    }

    case InteractionType.MessageComponent: {
      const comp = interaction as APIMessageComponentInteraction;

      if (comp.data.component_type === ComponentType.StringSelect) {
        const data = comp.data as APIMessageStringSelectInteractionData;

        // STEP 1: Year selected, show GP list
        if (data.custom_id === "select_year") {
          const year = data.values[0].trim();
          const gps = getGps(year);
          const uniqueGps = Array.from(new Set(gps));

          return c.json({
            type: InteractionResponseType.UpdateMessage,
            data: {
              content: `Year **${year}** selected. Select a Grand Prix:`,
              components: [
                {
                  type: 1,
                  components: [
                    {
                      type: ComponentType.StringSelect,
                      custom_id: `select_gp:${year}`,
                      options: uniqueGps.map((g) => ({
                        label: g,
                        value: g,
                      })),
                    },
                  ],
                },
              ],
            },
          });
        }

        // STEP 2: GP selected, show identifier (Qualifying, Sprint, Race)
        if (data.custom_id.startsWith("select_gp:")) {
          const [, year] = data.custom_id.split(":");
          const gp = data.values[0];
          const identifiers = ["Qualifying", "Sprint", "Race"];

          return c.json({
            type: InteractionResponseType.UpdateMessage,
            data: {
              content: `Grand Prix **${gp}** selected. Choose a session type:`,
              components: [
                {
                  type: 1,
                  components: [
                    {
                      type: ComponentType.StringSelect,
                      custom_id: `select_identifier:${year}:${gp}`,
                      options: identifiers.map((id) => ({
                        label: id,
                        value: id,
                      })),
                    },
                  ],
                },
              ],
            },
          });
        }

        // STEP 3: Identifier selected, fetch PNG and embed result
        if (data.custom_id.startsWith("select_identifier:")) {
          const [, year, gp] = data.custom_id.split(":");
          const identifier = data.values[0];

          const normalizedId = identifier.toLowerCase();

          const key = `${year}/${gp}/${normalizedId}.png`;
          const obj = await c.env.R2_BUCKET.get(key);

          if (!obj) {
            return c.json({
              type: InteractionResponseType.ChannelMessageWithSource,
              data: {
                flags: InteractionResponseFlags.EPHEMERAL,
                content: `No data found for ${gp} ${identifier} ${year}.`,
              },
            });
          }

          const blob = await obj.blob();
          const form = new FormData();
          form.append("file", blob, "result.png");
          form.append(
            "payload_json",
            JSON.stringify({
              flags: InteractionResponseFlags.EPHEMERAL,
              embeds: [
                {
                  title: `Result for ${gp} ${identifier} ${year}`,
                  image: { url: "attachment://result.png" },
                },
              ],
            }),
          );

          c.executionCtx.waitUntil(
            fetch(
              `https://discord.com/api/v10/webhooks/${comp.application_id}/${comp.token}`,
              {
                method: "POST",
                headers: { Authorization: `Bot ${c.env.TOKEN}` },
                body: form,
              },
            ),
          );

          return c.json({
            type: InteractionResponseType.UpdateMessage,
            data: {
              content: `Result for **${gp} ${identifier} ${year}**.`,
              components: [],
            },
          });
        }
      }
      break;
    }

    // Handles unsupported or unknown interaction types
    default:
      return c.json({ error: "Unknown Type" }, { status: 400 });
  }

  //--------------------------------------------------------------
  // Fallback
  //--------------------------------------------------------------
  console.error("Unknown Type");
  return c.json({ error: "Unknown Type" }, { status: 400 });
});

//--------------------------------------------------------------
// Other endpoints -> 404
//--------------------------------------------------------------
app.all("*", (c) => c.text("Not Found.", { status: 404 }));

export default app;
