import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";

export const metadata = {
  title: "Who we are — KOMPLYINT",
  description: "About KOMPLYINT OY — a compliance readiness company focused on preparation and clarity.",
};

export default function Page() {
  return (
    <Section>
      <Container>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          Who we are
        </h1>
        <p className="mt-3 max-w-xl text-base text-slate-600">
          Content will be added soon.
        </p>
      </Container>
    </Section>
  );
}
