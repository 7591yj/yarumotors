import { config } from "dotenv";
import process from "process";
import {
  APIApplicationCommand,
  RESTPostAPIApplicationCommandsJSONBody,
  Routes,
} from "discord-api-types/v10";
import * as commands from "./commands.js";

config({ path: ".env" });

const token =
  process.env.DISCORD_TOKEN ??
  (() => {
    throw new Error("DISCORD_TOKEN missing.");
  })();
const applicationId =
  process.env.DISCORD_APPLICATION_ID ??
  (() => {
    throw new Error("DISCORD_APPLICATION_ID missing.");
  })();

const commandList = Object.values(
  commands,
) as RESTPostAPIApplicationCommandsJSONBody[];

async function registerCommands(): Promise<void> {
  console.log(`Registering ${commandList.length} commands...`);
  for (const cmd of commandList) console.log(`→ ${cmd.name}`);

  const url = `https://discord.com/api/v10${Routes.applicationCommands(applicationId)}`;

  const res = await fetch(url, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bot ${token}`,
    },
    body: JSON.stringify(commandList),
  });

  if (!res.ok) {
    const errText = await res.text();
    throw new Error(
      `Registration failed: ${res.status} ${res.statusText}\n${errText}`,
    );
  }

  const data = (await res.json()) as APIApplicationCommand[];
  console.log(`Success. Registered ${data.length} commands.`);
  data.forEach((d, i) => console.log(`${i + 1}. ${d.name} (id: ${d.id})`));
}

void registerCommands();
