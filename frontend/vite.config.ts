import { defineConfig } from 'vite';

/** GitHub Pages uses a repository subpath; other hosts use '/'. */
export default defineConfig({
  base: process.env.GITHUB_PAGES === 'true' ? '/Ahmed-Alnahmi-711/' : '/',
});
