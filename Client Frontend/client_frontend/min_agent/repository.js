import { DatabaseSync } from "node:sqlite";
import { pathToFileURL } from "node:url";

import { createCoverageSnapshotRepository } from "./coverage_snapshot.js";
import { createDocumentRepository } from "./document_repository.js";
import { createImageRepository } from "./image_repository.js";
import { createOntologyReadRepository } from "./ontology_repository.js";
import { createProvenanceRepository } from "./provenance_repository.js";
import { createQueryRepository } from "./query_repository.js";
import { createSourceRepository } from "./source_repository.js";

export function createMinimalRepository({ dbPath, dataDir }) {
  const database = new DatabaseSync(`${pathToFileURL(dbPath).href}?mode=ro`);
  const imageRepository = createImageRepository({ database, dataDir });
  const queryRepository = createQueryRepository({ database });
  const sourceRepository = createSourceRepository({ database, imageRepository });
  return {
    ...queryRepository,
    ...createCoverageSnapshotRepository({ database }),
    ...createOntologyReadRepository({ database }),
    ...sourceRepository,
    ...createDocumentRepository({ database, buildSource: sourceRepository.buildSource, imageRepository }),
    ...createProvenanceRepository({ database, buildSource: sourceRepository.buildSource }),
    resolveImage(docId, page = 1) {
      return imageRepository.resolveImage(docId, page);
    },
    close() {
      database.close();
    }
  };
}
