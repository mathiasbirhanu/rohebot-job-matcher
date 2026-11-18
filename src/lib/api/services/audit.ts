import { listRecords } from "../records";

export interface SearchAuditLog {
  id: string;
  employerName: string;
  searchQuery: string;
  filtersUsed: string[];
  timestamp: string;
  resultsCount: number;
}

export const auditService = {
  getSearchAudits: (): Promise<SearchAuditLog[]> => listRecords("audit-logs"),
};
