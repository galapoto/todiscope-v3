import { EnginePage } from "@/components/engines/engine-page";

export default async function EngineDetailPage({
  params,
}: {
  params: Promise<{ engineId: string }>;
}) {
  const { engineId } = await params;
  return <EnginePage engineId={engineId} />;
}

