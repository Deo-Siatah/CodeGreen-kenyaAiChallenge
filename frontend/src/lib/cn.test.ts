import { describe, it, expect } from 'vitest';
import { cn } from './cn';

describe('cn utility function', () => {
  it('should merge class names correctly', () => {
    expect(cn('class1', 'class2')).toBe('class1 class2');
  });

  it('should filter out falsy values', () => {
    expect(cn('class1', false, 'class2', null, 'class3')).toBe('class1 class2 class3');
  });

  it('should handle conditional classes', () => {
    const isActive = true;
    expect(cn('class1', isActive && 'active-class', 'class2')).toBe('class1 active-class class2');
  });

  it('should handle array of classes', () => {
    expect(cn(['class1', 'class2'], 'class3')).toBe('class1 class2 class3');
  });

  it('should handle complex objects', () => {
    const condition = true;
    expect(cn(
      'base-class',
      condition && {
        'active-class': true,
        'inactive-class': false,
      },
      'extra-class'
    )).toBe('base-class active-class extra-class');
  });

  it('should handle empty input', () => {
    expect(cn()).toBe('');
    expect(cn('')).toBe('');
  });
});