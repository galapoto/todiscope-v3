import Container from "@/components/ui/Container";
import Section from "@/components/ui/Section";

export const metadata = {
  title: "What we do — KOMPLYINT",
  description: "KOMPLYINT OY provides compliance readiness support for organisations.",
};

export default function Page() {
  return (
    <Section>
      <Container>
        <h1 className="text-3xl font-semibold tracking-tight text-slate-900">
          What we do
        </h1>
        <p className="mt-3 max-w-xl text-base text-slate-600">
          Content will be added soon.
        </p>
      </Container>
    </Section>
  );
}
