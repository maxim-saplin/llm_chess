class MinimalMD {
    static async render(elementId) {
        try {
            console.log(`Attempting to render markdown to element: ${elementId}`);
            const element = document.getElementById(elementId);
            if (!element) {
                throw new Error(`Element with ID '${elementId}' not found`);
            }
            
            console.log('Fetching notes.md...');
            const response = await fetch('notes.md');
            if (!response.ok) {
                throw new Error(`Failed to load markdown: ${response.status}`);
            }
            
            const text = await response.text();
            console.log('Markdown content loaded, length:', text.length);
            
            const html = this.parseMarkdown(text);
            console.log('Markdown parsed, setting innerHTML');
            
            element.innerHTML = html;
            console.log('Markdown rendering complete');
        } catch (error) {
            console.error('Error loading markdown:', error);
            // Display a fallback message when notes.md can't be loaded
            const element = document.getElementById(elementId);
            if (element) {
                element.innerHTML = 
                    '<p class="descriptions">Notes content could not be loaded. Please check back later.</p>';
            }
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
                .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>')
                
                // Convert nested unordered lists (4 spaces before "-")
                .replace(/^( {4})-\s+(.+)$/gm, '<br>&nbsp;&nbsp;- $2')
                // Convert top-level unordered lists
                .replace(/\n\n-\s+(.+)/g, '<br><br>- $1')
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
