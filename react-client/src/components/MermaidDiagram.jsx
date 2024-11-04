import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

function MermaidDiagram({ definition }) {
    const elementRef = useRef(null);

    useEffect(() => {
        // Initialize mermaid
        mermaid.initialize({
            startOnLoad: true,
            theme: 'default',
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis',
                nodeSpacing: 50,
                rankSpacing: 50,
                padding: 8
            },
            securityLevel: 'loose' // This might be needed depending on your content
        });

        const renderDiagram = async () => {
            if (elementRef.current && definition) {
                try {
                    // Clear previous content
                    elementRef.current.innerHTML = '';

                    // Generate unique ID to avoid conflicts
                    const id = `mermaid-${Math.random().toString(36).substr(2, 9)}`;

                    // Render new diagram
                    const { svg } = await mermaid.render(id, definition);
                    elementRef.current.innerHTML = svg;
                } catch (error) {
                    console.error('Mermaid rendering failed:', error);
                    console.log('Definition:', definition);
                }
            }
        };

        renderDiagram();
    }, [definition]);

    return (
        <div
            ref={elementRef}
            style={{
                background: 'white',
                padding: '20px',
                borderRadius: '8px',
                boxShadow: '0 2px 4px rgba(0,0,0,0.1)',
                marginBottom: '20px'
            }}
        />
    );
}

export default MermaidDiagram;