"use server";

import { createAI, getMutableAIState } from "@ai-sdk/rsc";
import { ReactNode } from "react";
import { z } from "zod";
import { EventCarousel, EventData } from "./components/event-card";
import { WeatherEventCarousel, WeatherEventData } from "./components/weather-event-card";
import { WalkList } from "./components/walk-list";
import { CityWalkData } from "./components/city-walk";
import { Loader2 } from "lucide-react";

// --- 1. Define the AI State Types ---
export interface ServerMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ClientMessage {
  id: string;
  role: "user" | "assistant";
  display: ReactNode;
}

// --- 2. Zod Schemas for MCP Tools ---
const GetRotterdamEventsSchema = z.object({
  query: z.string().optional(),
  date: z.string().optional(),
});

const GetAmsterdamEventsSchema = z.object({
  query: z.string().optional(),
  date: z.string().optional(),
});

const GetCitySecretsSchema = z.object({
  city: z.string().optional(),
  type: z.enum(["walk", "event", "venue"]).optional(),
});

const GetTicketmasterEventsSchema = z.object({
  location: z.string(),
  radius: z.number().optional(),
  date: z.string().optional(),
});

// --- 3. Mock MCP Client Interface ---
interface MCPClient {
  name: string;
  delay: number; // Simulated network delay in ms
}

const MCP_CLIENTS: Record<string, MCPClient> = {
  "uitagenda-rotterdam": { name: "Uitagenda Rotterdam", delay: 600 },
  "mcp-iamsterdam": { name: "I Amsterdam", delay: 700 },
  "mcp-city-secrets": { name: "City Secrets", delay: 500 },
  "mcp-ticketmaster": { name: "Ticketmaster", delay: 800 },
};

// Simulate MCP call with delay
async function simulateMCPCall<T>(client: MCPClient, data: T): Promise<T> {
  await new Promise((resolve) => setTimeout(resolve, client.delay));
  return data;
}

// --- 4. Mock MCP Data Generators ---
// These simulate fetching data from your external MCP servers
const mockUitAgendaRotterdam = async (): Promise<EventData[]> => {
  const data: EventData[] = [
    {
      id: "rot-1",
      title: "Techno Bunker Night",
      image: "https://images.unsplash.com/photo-1574391884720-2e45549d7733?q=80&w=1000",
      time: "Tonight, 23:00",
      location: "Perron, Rotterdam",
      price: "€15.00",
      category: "Clubbing",
      source: "uitagenda-rotterdam",
      description:
        "Underground techno night featuring local and international DJs. Dark, industrial vibes.",
    },
    {
      id: "rot-2",
      title: "Jazz at Bird",
      image: "https://images.unsplash.com/photo-1511192336575-5a79af67a629?q=80&w=1000",
      time: "Tonight, 20:30",
      location: "Bird, Rotterdam",
      price: "Free",
      category: "Live Music",
      source: "uitagenda-rotterdam",
      description: "Intimate jazz session with local musicians. Cozy atmosphere, great cocktails.",
    },
    {
      id: "rot-3",
      title: "Theater Rotterdam: Modern Dance",
      image: "https://images.unsplash.com/photo-1508700115892-45ecd05ae2ad?q=80&w=1000",
      time: "Tonight, 20:00",
      location: "Theater Rotterdam",
      price: "€25.00",
      category: "Theater",
      source: "uitagenda-rotterdam",
      description: "Contemporary dance performance exploring urban movement and rhythm.",
    },
  ];
  return simulateMCPCall(MCP_CLIENTS["uitagenda-rotterdam"], data);
};

const mockIAmsterdam = async (): Promise<EventData[]> => {
  const data: EventData[] = [
    {
      id: "ams-1",
      title: "Rijksmuseum Late Night",
      image: "https://images.unsplash.com/photo-1554907984-15263bfd63bd?q=80&w=1000",
      time: "Tonight, 19:00 - 22:00",
      location: "Museumplein, Amsterdam",
      price: "€22.50",
      category: "Culture",
      source: "mcp-iamsterdam",
      description:
        "Extended evening hours at the Rijksmuseum. Special guided tours and live music in the galleries.",
    },
    {
      id: "ams-2",
      title: "Canal Light Tour",
      image: "https://images.unsplash.com/photo-1588733103629-b77afeaf847d?q=80&w=1000",
      time: "Starts every 30 mins",
      location: "Central Station",
      price: "€18.00",
      category: "Sightseeing",
      source: "mcp-iamsterdam",
      description:
        "Evening canal cruise with illuminated bridges and historic commentary. Romantic atmosphere.",
    },
    {
      id: "ams-3",
      title: "Van Gogh Museum: Night Viewing",
      image: "https://images.unsplash.com/photo-1578301978162-7aae4d755744?q=80&w=1000",
      time: "Tonight, 19:00 - 21:00",
      location: "Museumplein, Amsterdam",
      price: "€20.00",
      category: "Culture",
      source: "mcp-iamsterdam",
      description: "Special evening viewing with fewer crowds. Audio guide included.",
    },
  ];
  return simulateMCPCall(MCP_CLIENTS["mcp-iamsterdam"], data);
};

const mockCitySecrets = async (): Promise<CityWalkData[]> => {
  const data: CityWalkData[] = [
    {
      id: "secret-1",
      title: "Hidden Speakeasy Walk",
      description:
        "Discover Amsterdam's best-kept secret bars and hidden cocktail lounges in the historic Jordaan district.",
      distance: "2.5 km",
      duration: "1.5 hours",
      location: "Jordaan District, Amsterdam",
      route: {
        name: "Speakeasy Trail",
        waypoints: [
          "Start: Café de Reiger",
          "Door 74 (Secret entrance)",
          "Hiding in Plain Sight",
          "Tales & Spirits",
          "End: Proeflokaal A. van Wees",
        ],
      },
      difficulty: "Easy",
      source: "mcp-city-secrets",
    },
    {
      id: "secret-2",
      title: "Rotterdam Street Art Discovery",
      description:
        "Explore the vibrant street art scene in Rotterdam's Witte de Withstraat and surrounding areas.",
      distance: "3.0 km",
      duration: "2 hours",
      location: "Witte de Withstraat, Rotterdam",
      route: {
        name: "Art Walk",
        waypoints: [
          "Start: Witte de Withstraat",
          "Mural at WORM",
          "Underground Gallery",
          "Hidden Courtyard Art",
          "End: TENT Rotterdam",
        ],
      },
      difficulty: "Moderate",
      source: "mcp-city-secrets",
    },
    {
      id: "secret-3",
      title: "Romantic Canal Walk",
      description:
        "A peaceful evening stroll along Amsterdam's lesser-known canals, away from the crowds.",
      distance: "4.0 km",
      duration: "1.5 hours",
      location: "Nine Streets, Amsterdam",
      route: {
        name: "Romantic Route",
        waypoints: [
          "Start: Prinsengracht",
          "Herengracht",
          "Keizersgracht",
          "Bloemgracht",
          "End: Jordaan",
        ],
      },
      difficulty: "Easy",
      source: "mcp-city-secrets",
    },
  ];
  return simulateMCPCall(MCP_CLIENTS["mcp-city-secrets"], data);
};

const mockTicketmaster = async (location: string): Promise<EventData[]> => {
  const data: EventData[] = [
    {
      id: "tm-1",
      title: "Indie Rock Night",
      image: "https://images.unsplash.com/photo-1470229722913-7c0e2dbbaf53?q=80&w=1000",
      time: "Tonight, 20:00",
      location: "Paradiso, Amsterdam",
      price: "€35.00",
      category: "Concert",
      source: "mcp-ticketmaster",
      description:
        "Live indie rock performance featuring emerging artists. Limited tickets available.",
    },
    {
      id: "tm-2",
      title: "Electronic Music Festival",
      image: "https://images.unsplash.com/photo-1470229722913-7c0e2dbbaf53?q=80&w=1000",
      time: "Tonight, 22:00",
      location: "Maassilo, Rotterdam",
      price: "€45.00",
      category: "Concert",
      source: "mcp-ticketmaster",
      description: "Major electronic music event with international DJs. Warehouse venue.",
    },
  ];
  return simulateMCPCall(MCP_CLIENTS["mcp-ticketmaster"], data);
};

const mockWeatherEvents = async (): Promise<WeatherEventData[]> => {
  const data: WeatherEventData[] = [
    {
      id: "weather-1",
      location: "Rotterdam, Netherlands",
      weatherType: "sun",
      temperature: "24°C",
      condition: "Sunny",
      precipitation: "10%",
      humidity: "65%",
      windSpeed: "12 km/h",
    },
    {
      id: "weather-2",
      location: "Amsterdam, Netherlands",
      weatherType: "rain",
      temperature: "15°C",
      condition: "Light Rain",
      precipitation: "75%",
      humidity: "85%",
      windSpeed: "18 km/h",
    },
    {
      id: "weather-3",
      location: "The Hague, Netherlands",
      weatherType: "wind",
      temperature: "18°C",
      condition: "Windy",
      precipitation: "20%",
      humidity: "70%",
      windSpeed: "26 km/h",
    },
    {
      id: "weather-4",
      location: "Utrecht, Netherlands",
      weatherType: "snow",
      temperature: "-2°C",
      condition: "Snow",
      precipitation: "90%",
      humidity: "95%",
      windSpeed: "15 km/h",
    },
    {
      id: "weather-5",
      location: "Eindhoven, Netherlands",
      weatherType: "clouds",
      temperature: "19°C",
      condition: "Cloudy",
      precipitation: "40%",
      humidity: "75%",
      windSpeed: "14 km/h",
    },
    {
      id: "weather-6",
      location: "Groningen, Netherlands",
      weatherType: "fog",
      temperature: "12°C",
      condition: "Foggy",
      precipitation: "30%",
      humidity: "90%",
      windSpeed: "8 km/h",
    },
    {
      id: "weather-7",
      location: "Maastricht, Netherlands",
      weatherType: "storm",
      temperature: "16°C",
      condition: "Thunderstorm",
      precipitation: "95%",
      humidity: "88%",
      windSpeed: "32 km/h",
    },
    {
      id: "weather-8",
      location: "Haarlem, Netherlands",
      weatherType: "clear",
      temperature: "22°C",
      condition: "Clear",
      precipitation: "5%",
      humidity: "60%",
      windSpeed: "10 km/h",
    },
  ];
  return simulateMCPCall({ name: "Weather MCP", delay: 500 }, data);
};

// --- 5. The Main Server Action ---
export async function submitUserMessage(input: string) {
  "use server";

  const aiState = getMutableAIState();
  aiState.update([...aiState.get(), { role: "user", content: input }]);

  // In a real app, you would use 'openai' provider here.
  // We are simulating the "Tool Call" decision logic to allow this demo to run without API keys.

  const lowerInput = input.toLowerCase();

  let toolToCall = "";
  let toolParams: any = {};

  // Enhanced tool detection logic
  if (
    lowerInput.includes("weather") ||
    lowerInput.includes("rain") ||
    lowerInput.includes("sun") ||
    lowerInput.includes("snow") ||
    lowerInput.includes("wind") ||
    lowerInput.includes("storm") ||
    lowerInput.includes("cloud") ||
    lowerInput.includes("fog") ||
    lowerInput.includes("clear")
  ) {
    toolToCall = "get_weather_events";
  } else if (lowerInput.includes("rotterdam")) {
    toolToCall = "get_rotterdam_events";
    if (lowerInput.includes("concert") || lowerInput.includes("music")) {
      toolParams.type = "music";
    }
  } else if (lowerInput.includes("amsterdam")) {
    toolToCall = "get_amsterdam_events";
    if (lowerInput.includes("museum") || lowerInput.includes("culture")) {
      toolParams.type = "culture";
    }
  } else if (
    lowerInput.includes("walk") ||
    lowerInput.includes("secret") ||
    lowerInput.includes("hidden")
  ) {
    toolToCall = "get_city_secrets";
    if (lowerInput.includes("amsterdam")) toolParams.city = "amsterdam";
    if (lowerInput.includes("rotterdam")) toolParams.city = "rotterdam";
  } else if (
    lowerInput.includes("concert") ||
    lowerInput.includes("ticketmaster") ||
    lowerInput.includes("tickets")
  ) {
    toolToCall = "get_ticketmaster_events";
    if (lowerInput.includes("amsterdam")) toolParams.location = "Amsterdam";
    else if (lowerInput.includes("rotterdam")) toolParams.location = "Rotterdam";
    else toolParams.location = "Amsterdam"; // Default
  } else {
    toolToCall = "default_chat";
  }

  // Simulate AI processing delay
  await new Promise((resolve) => setTimeout(resolve, 300));

  // Manual Dispatch based on our Mock Logic
  // In real Vercel AI SDK, the LLM selects these tools automatically via streamUI.
  // For this demo, we manually determine the response to bypass API keys.
  let responseUI: ReactNode;

  try {
    switch (toolToCall) {
      case "get_weather_events": {
        const weatherEvents = await mockWeatherEvents();
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90 mb-2">Here are some weather-appropriate activities:</p>
            <WeatherEventCarousel events={weatherEvents} />
          </div>
        );
        break;
      }
      case "get_rotterdam_events": {
        const events = await mockUitAgendaRotterdam();
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90 mb-2">
              I found some great vibes in Rotterdam for you:
            </p>
            <EventCarousel events={events} />
          </div>
        );
        break;
      }
      case "get_amsterdam_events": {
        const events = await mockIAmsterdam();
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90 mb-2">
              Here is what's happening in Amsterdam tonight:
            </p>
            <EventCarousel events={events} />
          </div>
        );
        break;
      }
      case "get_city_secrets": {
        const walks = await mockCitySecrets();
        // Filter by city if specified
        const filteredWalks = toolParams.city
          ? walks.filter((w) => w.location.toLowerCase().includes(toolParams.city))
          : walks;
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90 mb-2">
              Looking for something hidden? Check these out:
            </p>
            <WalkList walks={filteredWalks} />
          </div>
        );
        break;
      }
      case "get_ticketmaster_events": {
        const events = await mockTicketmaster(toolParams.location || "Amsterdam");
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90 mb-2">
              Concert tickets available in {toolParams.location}:
            </p>
            <EventCarousel events={events} />
          </div>
        );
        break;
      }
      default:
        responseUI = (
          <div className="space-y-2 animate-[fadeIn_0.3s_ease-out]">
            <p className="text-foreground/90">
              I can help you find things to do in{" "}
              <strong className="text-foreground">Rotterdam</strong> or{" "}
              <strong className="text-foreground">Amsterdam</strong>.
            </p>
            <p className="text-foreground/80 text-sm">Try asking:</p>
            <ul className="text-foreground/80 text-sm list-disc list-inside space-y-1 ml-2">
              <li>"What's happening in Rotterdam tonight?"</li>
              <li>"Show me walks in Amsterdam"</li>
              <li>"Concerts in Amsterdam"</li>
              <li>"Show me weather events" or "What to do in the rain?"</li>
            </ul>
          </div>
        );
    }
  } catch (error) {
    console.error("Error fetching MCP data:", error);
    responseUI = (
      <p className="text-destructive">Sorry, there was an error fetching data. Please try again.</p>
    );
  }

  aiState.done([
    ...aiState.get(),
    { role: "assistant", content: `Displaying UI for ${toolToCall}` },
  ]);

  return {
    id: Date.now().toString(),
    display: responseUI,
  };
}

// --- 4. Create the AI Context ---
export const AI = createAI<
  ServerMessage[],
  ClientMessage[],
  { submitUserMessage: typeof submitUserMessage }
>({
  actions: {
    submitUserMessage,
  },
  initialUIState: [],
  initialAIState: [],
});
