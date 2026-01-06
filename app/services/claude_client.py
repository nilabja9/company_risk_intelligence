import anthropic
from typing import Any

from app.config import get_settings


class ClaudeClient:
    def __init__(self):
        self.settings = get_settings()
        self.model = "claude-sonnet-4-20250514"
        self._api_key = self.settings.anthropic_api_key
        self._client = None

    @property
    def client(self):
        if self._client is None:
            if not self._api_key or self._api_key == "YOUR_ANTHROPIC_API_KEY_HERE":
                raise ValueError(
                    "Anthropic API key not configured. "
                    "Please set ANTHROPIC_API_KEY in your .env file. "
                    "Get a key at: https://console.anthropic.com/settings/keys"
                )
            self._client = anthropic.Anthropic(api_key=self._api_key)
        return self._client

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key and self._api_key != "YOUR_ANTHROPIC_API_KEY_HERE")

    def generate(
        self,
        prompt: str,
        system: str | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7
    ) -> str:
        messages = [{"role": "user", "content": prompt}]

        kwargs = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": messages,
            "temperature": temperature,
        }

        if system:
            kwargs["system"] = system

        response = self.client.messages.create(**kwargs)

        return response.content[0].text

    def analyze_risks(self, filing_text: str, company_name: str) -> dict:
        system = """You are a financial analyst specializing in SEC filing analysis.
        Analyze the provided text and identify key risks and red flags.
        Return your analysis as structured JSON."""

        prompt = f"""Analyze the following SEC filing excerpt for {company_name}.
        Identify and categorize risks into these categories:
        - REGULATORY: Regulatory and compliance risks
        - LITIGATION: Legal proceedings and litigation risks
        - FINANCIAL: Financial and credit risks
        - OPERATIONAL: Operational and business risks
        - MARKET: Market and competitive risks
        - ACCOUNTING: Accounting and reporting concerns

        For each risk found, provide:
        - category: One of the categories above
        - severity: LOW, MEDIUM, or HIGH
        - description: Brief description of the risk
        - evidence: Quote from the text supporting this finding

        Return as JSON with format: {{"risks": [...]}}

        Filing text:
        {filing_text[:8000]}
        """

        response = self.generate(prompt, system=system, temperature=0.3)

        # Parse JSON from response
        try:
            import json
            # Extract JSON from response
            json_match = response.find("{")
            if json_match != -1:
                json_str = response[json_match:]
                json_end = json_str.rfind("}") + 1
                return json.loads(json_str[:json_end])
        except:
            pass

        return {"risks": [], "error": "Failed to parse response"}

    def extract_financial_metrics(self, filing_text: str, company_name: str) -> dict:
        system = """You are a financial analyst specializing in extracting
        structured financial data from SEC filings.
        Extract precise numerical values and return as structured JSON."""

        prompt = f"""Extract the following financial metrics from this SEC filing for {company_name}.

        Required metrics (extract actual values, use null if not found):
        - revenue: Total revenue/net sales
        - gross_profit: Gross profit
        - operating_income: Operating income
        - net_income: Net income
        - total_assets: Total assets
        - total_liabilities: Total liabilities
        - shareholders_equity: Total shareholders' equity
        - total_debt: Total debt (long-term + short-term)
        - current_assets: Current assets
        - current_liabilities: Current liabilities
        - inventory: Total inventory
        - ebit: Earnings before interest and taxes
        - interest_expense: Interest expense
        - eps: Earnings per share (diluted)

        For each metric, provide:
        - value: The numerical value (in millions USD unless specified)
        - period: The fiscal period (e.g., "FY2023", "Q3 2023")
        - source: Brief quote showing where this was found

        Return as JSON: {{"metrics": {{"metric_name": {{"value": X, "period": "...", "source": "..."}}}}}}

        Filing text:
        {filing_text[:10000]}
        """

        response = self.generate(prompt, system=system, temperature=0.1)

        try:
            import json
            json_match = response.find("{")
            if json_match != -1:
                json_str = response[json_match:]
                json_end = json_str.rfind("}") + 1
                return json.loads(json_str[:json_end])
        except:
            pass

        return {"metrics": {}, "error": "Failed to parse response"}

    def answer_question(
        self,
        question: str,
        context_chunks: list[dict],
        company_name: str
    ) -> dict:
        system = """You are a helpful financial analyst assistant.
        Answer questions about companies based on their SEC filings.
        Always cite your sources and be precise with financial information.
        If you're uncertain, say so clearly."""

        # Build context from chunks
        context = "\n\n---\n\n".join([
            f"[Source: {c.get('section_name', 'Unknown')} - {c.get('filing_type', '')} filed {c.get('filing_date', '')}]\n{c.get('chunk_text', '')}"
            for c in context_chunks
        ])

        prompt = f"""Based on the following SEC filing excerpts for {company_name},
        answer this question: {question}

        Context from SEC filings:
        {context}

        Provide a clear, concise answer. Include specific citations to the filing sections.
        If the context doesn't contain enough information to answer fully, say so.

        Format your response as JSON:
        {{
            "answer": "Your detailed answer here",
            "confidence": "HIGH/MEDIUM/LOW",
            "sources": ["List of sections/filings used"],
            "caveats": ["Any limitations or uncertainties"]
        }}
        """

        response = self.generate(prompt, system=system, temperature=0.3)

        try:
            import json
            json_match = response.find("{")
            if json_match != -1:
                json_str = response[json_match:]
                json_end = json_str.rfind("}") + 1
                return json.loads(json_str[:json_end])
        except:
            pass

        return {
            "answer": response,
            "confidence": "LOW",
            "sources": [],
            "caveats": ["Response parsing failed"]
        }

    def summarize_changes(
        self,
        current_text: str,
        previous_text: str,
        section_name: str,
        company_name: str
    ) -> dict:
        system = """You are a financial analyst tracking changes in SEC filings.
        Compare two versions of a filing section and identify significant changes."""

        prompt = f"""Compare these two versions of the {section_name} section for {company_name}.

        PREVIOUS VERSION:
        {previous_text[:5000]}

        CURRENT VERSION:
        {current_text[:5000]}

        Identify:
        1. New risks or concerns added
        2. Risks removed or reduced
        3. Changes in language tone or severity
        4. New legal or regulatory mentions
        5. Any red flags

        Return as JSON:
        {{
            "summary": "Brief overall summary of changes",
            "additions": ["List of new content/risks"],
            "removals": ["List of removed content"],
            "tone_changes": ["Notable changes in language"],
            "red_flags": ["Any concerning changes"],
            "significance": "HIGH/MEDIUM/LOW"
        }}
        """

        response = self.generate(prompt, system=system, temperature=0.3)

        try:
            import json
            json_match = response.find("{")
            if json_match != -1:
                json_str = response[json_match:]
                json_end = json_str.rfind("}") + 1
                return json.loads(json_str[:json_end])
        except:
            pass

        return {"summary": response, "significance": "UNKNOWN"}


def get_claude_client() -> ClaudeClient:
    return ClaudeClient()
