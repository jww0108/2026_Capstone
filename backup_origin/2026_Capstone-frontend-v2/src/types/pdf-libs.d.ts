declare module "html2canvas" {
  const html2canvas: (element: HTMLElement, options?: Record<string, unknown>) => Promise<HTMLCanvasElement>
  export default html2canvas
}

declare module "jspdf" {
  export class jsPDF {
    constructor(options?: Record<string, unknown>)
    internal: {
      pageSize: {
        getWidth: () => number
        getHeight: () => number
      }
    }
    addImage: (...args: unknown[]) => void
    addPage: () => void
    save: (filename: string) => void
  }
}
