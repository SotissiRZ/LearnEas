"use client";
import EmployerNav from "@/components/opportunities/EmployerNav";
import EmployerOpportunityForm from "@/components/opportunities/EmployerOpportunityForm";
import { useAuthGuard } from "@/hooks/useAuthGuard";
import GuardScreen from "@/components/ui/GuardScreen";
export default function NewOpportunityPage(){const {ready}=useAuthGuard();if(!ready)return <GuardScreen/>;return <div className="container-app py-10"><EmployerNav/><div className="mb-6"><h1 className="text-2xl font-extrabold">Nouvelle opportunité</h1><p className="mt-1 text-sm text-gray-500">Créez un brouillon puis soumettez-le à la modération LearnEas.</p></div><EmployerOpportunityForm/></div>}
