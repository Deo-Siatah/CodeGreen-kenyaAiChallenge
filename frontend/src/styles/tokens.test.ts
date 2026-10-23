import { describe, it, expect, beforeEach } from 'vitest';
import { readFileSync } from 'fs';
import { join, dirname } from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

describe('Design Tokens', () => {
  let cssContent: string;

  beforeEach(() => {
    // Read the CSS file content
    const filePath = join(__dirname, 'tokens.css');
    cssContent = readFileSync(filePath, 'utf-8');
  });

  it('should have CSS variables defined', () => {
    // Test background color variables
    expect(cssContent).toContain('--background:');
    expect(cssContent).toContain('--foreground:');
    
    // Test primary color variables
    expect(cssContent).toContain('--primary:');
    expect(cssContent).toContain('--primary-foreground:');
    
    // Test secondary color variables
    expect(cssContent).toContain('--secondary:');
    expect(cssContent).toContain('--secondary-foreground:');
    
    // Test border and input variables
    expect(cssContent).toContain('--border:');
    expect(cssContent).toContain('--input:');
    expect(cssContent).toContain('--ring:');
  });

  it('should have custom night harvest theme variables', () => {
    // Test custom theme variables
    expect(cssContent).toContain('--canvas:');
    expect(cssContent).toContain('--node-glow:');
    expect(cssContent).toContain('--edge-line:');
    expect(cssContent).toContain('--text-primary:');
    expect(cssContent).toContain('--text-secondary:');
  });

  it('should have font-family classes defined', () => {
    expect(cssContent).toContain('.font-sans');
    expect(cssContent).toContain('.font-serif');
    expect(cssContent).toContain('.font-mono');
    
    expect(cssContent).toContain('Hanken Grotesk');
    expect(cssContent).toContain('Fraunces');
    expect(cssContent).toContain('JetBrains Mono');
  });

  it('should have custom utility classes', () => {
    expect(cssContent).toContain('.text-glow');
    expect(cssContent).toContain('.node-glow');
    
    expect(cssContent).toContain('text-shadow:');
    expect(cssContent).toContain('filter:');
  });

  it('should self-host the variable fonts', () => {
    const entry = readFileSync(join(__dirname, '..', 'main.tsx'), 'utf-8');
    expect(entry).toContain("import '@fontsource-variable/fraunces'");
    expect(entry).toContain("import '@fontsource-variable/hanken-grotesk'");
    expect(entry).toContain("import '@fontsource-variable/jetbrains-mono'");
    expect(cssContent).not.toContain('fonts.googleapis.com');
  });

  it('should respect prefers-reduced-motion', () => {
    expect(cssContent).toContain('@media (prefers-reduced-motion: reduce)');
  });
});