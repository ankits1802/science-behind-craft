import nextVitals from "eslint-config-next/core-web-vitals";

const config = [
  {
    ignores: [".next/**", "node_modules/**", "next-env.d.ts", "public/monographs/kit/vendor/**"]
  },
  ...nextVitals,
  {
    rules: {
      "react-hooks/set-state-in-effect": "off"
    }
  },
  {
    files: ["components/editorial/**/*.tsx", "components/ui/Lightbox.tsx", "app/design/**/*.tsx"],
    rules: {
      "@next/next/no-img-element": "off"
    }
  }
];

export default config;
