import { safeGet } from "@/lib/api";
import { InteractiveFormation, Paginated } from "@/types";
import FormationCard from "@/components/formation/FormationCard";
import ApiErrorBanner from "@/components/ui/ApiErrorBanner";
import { Video } from "lucide-react";

export default async function FormationsPage() {
  const result = await safeGet<Paginated<InteractiveFormation> | InteractiveFormation[]>(
    "/formations/?ordering=start_date",
    []
  );
  const formations: InteractiveFormation[] = Array.isArray(result.data) ? result.data : result.data.results;

  return (
    <div className="container-app py-10">
      {!result.ok && <ApiErrorBanner message={result.error} />}

      <div className="mb-6 flex items-center gap-3">
        <div className="grid h-11 w-11 place-items-center rounded-xl bg-violet-50 text-violet-600">
          <Video size={22} />
        </div>
        <div>
          <h1 className="text-3xl font-extrabold">Formations interactives</h1>
          <p className="mt-1 text-gray-500">
            Séances en direct par visioconférence avec un instructeur, en petit groupe.
          </p>
        </div>
      </div>

      {formations.length === 0 ? (
        <div className="card p-10 text-center text-gray-500">
          {result.ok
            ? "Aucune formation interactive disponible pour le moment."
            : "Le catalogue n'a pas pu être chargé."}
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-6 sm:grid-cols-2 xl:grid-cols-3">
          {formations.map((f) => <FormationCard key={f.id} formation={f} />)}
        </div>
      )}
    </div>
  );
}
