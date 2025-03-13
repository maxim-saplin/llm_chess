class MinimalMD {
    static async render(elementId) {
        try {
            const response = await fetch('notes.md');
            const text = await response.text();
            const html = this.parseMarkdown(text);
            document.getElementById(elementId).innerHTML = html;
        } catch (error) {
            console.error('Error loading markdown:', error);
        }
    }

    static parseMarkdown(md) {
        // Split into sections by h1 headers
        const sections = md.split(/^# /m).filter(Boolean);
        
        return sections.map(section => {
            const [title, ...content] = section.split('\n');
            const contentHtml = content.join('\n')
                // Preserve HTML blocks by temporarily replacing them
                .replace(/(<div[\s\S]*?<\/div>)/g, (match, p1) => `__HTML_BLOCK_${btoa(p1)}__`)
                
                // Convert inline code
                .replace(/`([^`]+)`/g, '<em>$1</em>')

                .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
                
                // Convert URLs
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2">$1</a>')
                
                // Convert unordered lists
                .replace(/^\s*-\s+(.+)$/gm, '<br>- $1')
                
                // Convert line breaks
                .replace(/\n\n/g, '<br><br>')
                
                // Restore HTML blocks
                .replace(/__HTML_BLOCK_(.+?)__/g, (match, p1) => atob(p1));

            // Create ASCII header
            return `<span style="color:white;">
-------------------<br>
${title}<br>
-------------------<br><br></span>
${contentHtml}`;
        }).join('<br>');
    }
}
