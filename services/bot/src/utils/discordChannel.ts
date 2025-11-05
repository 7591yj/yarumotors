import { Bindings } from "../types/configuration";
import {
  APIChannel,
  APIMessage,
  RESTPostAPIGuildChannelJSONBody,
  APIEmbed,
} from "discord-api-types/v10";

export async function getOrCreateYarumotorsChannel(
  env: Bindings,
): Promise<string> {
  const apiBase = "https://discord.com/api/v10";
  const headers = {
    Authorization: `Bot ${env.TOKEN}`,
    "Content-Type": "application/json",
  };

  const stored = await env.STORE.get("yarumotors_channel");
  if (stored) return stored;

  const channelsResp = await fetch(
    `${apiBase}/guilds/${env.GUILD_ID}/channels`,
    { headers },
  );

  if (!channelsResp.ok)
    throw new Error(`Failed to list channels: ${channelsResp.statusText}`);

  const channels = await channelsResp.json();
  const found = channels.find((c: APIChannel) => c.name === "yarumotors");
  if (found) {
    await env.STORE.put("yarumotors_channel", found.id);
    return found.id;
  }

  const createBody: RESTPostAPIGuildChannelJSONBody = {
    name: "yarumotors",
    type: 0,
    topic: "Automated results from Yarumotors bot",
  };

  const createResp = await fetch(`${apiBase}/guilds/${env.GUILD_ID}/channels`, {
    method: "POST",
    headers,
    body: JSON.stringify(createBody),
  });

  if (!createResp.ok)
    throw new Error(`Failed to create channel: ${createResp.statusText}`);

  const created = await createResp.json();
  await env.STORE.put("yarumotors_channel", created.id);
  return created.id;
}

export async function getOrCreateYarumotorsMessage(
  env: Bindings,
  channelId: string,
  embed: APIEmbed,
): Promise<string> {
  const apiBase = "https://discord.com/api/v10";
  const headers = {
    Authorization: `Bot ${env.TOKEN}`,
    "Content-Type": "application/json",
  };

  const stored = await env.STORE.get("yarumotors_message");
  if (stored) return stored;

  const sendResp = await fetch(`${apiBase}/channels/${channelId}/messages`, {
    method: "POST",
    headers,
    body: JSON.stringify({ embeds: [embed] }),
  });

  if (!sendResp.ok)
    throw new Error(`Failed to send message: ${sendResp.statusText}`);

  const sent: APIMessage = await sendResp.json();
  await env.STORE.put("yarumotors_message", sent.id);
  return sent.id;
}

export async function updateYarumotorsMessage(env: Bindings, embed: APIEmbed) {
  const apiBase = "https://discord.com/api/v10";
  const headers = {
    Authorization: `Bot ${env.TOKEN}`,
    "Content-Type": "application/json",
  };

  const channelId = await env.STORE.get("yarumotors_channel");
  const messageId = await env.STORE.get("yarumotors_message");
  if (!channelId || !messageId) return;

  const resp = await fetch(
    `${apiBase}/channels/${channelId}/messages/${messageId}`,
    {
      method: "PATCH",
      headers,
      body: JSON.stringify({ embeds: [embed] }),
    },
  );

  if (!resp.ok) throw new Error(`Failed to update message: ${resp.statusText}`);
}
