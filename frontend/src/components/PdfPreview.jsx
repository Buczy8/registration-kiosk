import {useEffect, useRef, useState} from "react";
import {getDocument, GlobalWorkerOptions} from "pdfjs-dist";
import pdfWorker from "pdfjs-dist/build/pdf.worker.min.mjs?url";

GlobalWorkerOptions.workerSrc = pdfWorker;

const PAGE_GAP_PX = 8;

async function loadPageSizes(pdf) {
    const sizes = [];
    for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber += 1) {
        const page = await pdf.getPage(pageNumber);
        const viewport = page.getViewport({scale: 1});
        sizes.push({page, width: viewport.width, height: viewport.height});
    }
    return sizes;
}

function calculateWidthScale(pageSizes, contentWidth) {
    const naturalWidth = Math.max(...pageSizes.map((page) => page.width));
    return contentWidth / naturalWidth;
}

function getContentWidth(container) {
    const styles = getComputedStyle(container);
    const paddingX = parseFloat(styles.paddingLeft) + parseFloat(styles.paddingRight);
    return container.clientWidth - paddingX;
}

export default function PdfPreview({blob, title = "Podgląd dokumentu PDF"}) {
    const containerRef = useRef(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        let cancelled = false;
        let resizeObserver = null;
        let renderId = 0;
        const container = containerRef.current;

        if (!blob || !container) {
            return undefined;
        }

        async function renderPdf() {
            setLoading(true);
            setError(null);
            container.replaceChildren();

            try {
                const pdf = await getDocument({data: await blob.arrayBuffer()}).promise;
                if (cancelled) {
                    return;
                }

                const pageSizes = await loadPageSizes(pdf);
                if (cancelled) {
                    return;
                }

                const renderAtCurrentSize = async () => {
                    if (cancelled) return;

                    const currentRenderId = ++renderId;

                    const containerWidth = getContentWidth(container);
                    if (!containerWidth) return;

                    const baseScale = calculateWidthScale(pageSizes, containerWidth);
                    const pixelRatio = window.devicePixelRatio || 1;

                    container.replaceChildren();

                    for (const {page} of pageSizes) {
                        const renderViewport = page.getViewport({scale: baseScale * pixelRatio});
                        const cssViewport = page.getViewport({scale: baseScale});

                        const canvas = document.createElement("canvas");

                        canvas.width = Math.floor(renderViewport.width);
                        canvas.height = Math.floor(renderViewport.height);

                        canvas.style.width = `${Math.floor(cssViewport.width)}px`;
                        canvas.style.height = `${Math.floor(cssViewport.height)}px`;

                        canvas.className = "pdf-preview-page";

                        await page.render({
                            canvasContext: canvas.getContext("2d"),
                            viewport: renderViewport
                        }).promise;

                        if (cancelled || currentRenderId !== renderId) {
                            return;
                        }

                        container.appendChild(canvas);
                    }
                };

                await renderAtCurrentSize();
                if (cancelled) return;

                resizeObserver = new ResizeObserver(() => {
                    void renderAtCurrentSize();
                });
                resizeObserver.observe(container);

                setLoading(false);
            } catch (renderError) {
                if (!cancelled) {
                    setError(renderError.message);
                    setLoading(false);
                }
            }
        }

        void renderPdf();

        return () => {
            cancelled = true;
            resizeObserver?.disconnect();
            container.replaceChildren();
        };
    }, [blob]);

    return (
        <div className="pdf-preview" aria-label={title}>
            {loading && <p className="pdf-preview-status">Ładowanie podglądu...</p>}
            {error && (
                <p className="alert pdf-preview-status" role="alert">
                    Nie udało się wyświetlić PDF: {error}
                </p>
            )}
            <div className="pdf-preview-canvas-stack" ref={containerRef}/>
        </div>
    );
}
