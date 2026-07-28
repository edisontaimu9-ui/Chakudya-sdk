export declare const DEFAULT_BASE_URL: string;

export interface ChakudyaClientOptions {
  adminKey?: string;
  timeoutMs?: number;
}

export declare class ChakudyaApiError extends Error {
  status?: number;
  body?: unknown;
  constructor(message: string, status?: number, body?: unknown);
}

export interface CrudResource<T = any> {
  list(params?: Record<string, any>): Promise<T[]>;
  get(id: string | number): Promise<T>;
  create(payload: Partial<T>): Promise<T>;
  update(id: string | number, payload: Partial<T>): Promise<T>;
  remove(id: string | number): Promise<any>;
  replace?(id: string | number, payload: Partial<T>): Promise<T>;
}

export interface FoodsResource extends CrudResource {
  lookup(params: { q: string; [key: string]: any }): Promise<any>;
}

export interface PackagedResource {
  list(params?: Record<string, any>): Promise<any>;
  submit(payload: Record<string, any>): Promise<any>;
  scan(images: string[]): Promise<any>;
  update(id: string | number, payload: Record<string, any>): Promise<any>;
  remove(id: string | number): Promise<any>;
}

export interface RagResource {
  retrieve(
    query: string,
    options?: { context?: "both" | "oasis" | "thanzi"; topK?: number }
  ): Promise<any>;
  ingest(payload: {
    content: string;
    source: string;
    context?: "both" | "oasis" | "thanzi";
    metadata?: Record<string, any>;
  }): Promise<any>;
}

export interface MemoryResource {
  write(
    sessionId: string,
    content: string,
    options?: { kind?: string; patientLabel?: string }
  ): Promise<any>;
  recall(
    sessionId: string,
    query: string,
    options?: { topK?: number }
  ): Promise<any>;
  consolidate(sessionId: string): Promise<any>;
}

export declare class ChakudyaClient {
  baseUrl: string;
  adminKey: string | null;
  timeoutMs: number;

  foods: FoodsResource;
  exchange: CrudResource;
  renal: CrudResource;
  formulas: CrudResource;
  manufacturers: CrudResource;
  products: CrudResource;
  packaged: PackagedResource;
  nutrition: { get(productId: string | number): Promise<any> };
  rag: RagResource;
  memory: MemoryResource;

  constructor(baseUrl: string, options?: ChakudyaClientOptions);
  root(): Promise<any>;
}

declare const chakudya: ChakudyaClient;
export { chakudya };
export default chakudya;
