"""Compare two views of a parsed LaTeX expression, then edit through one."""

from TexSoup import TexSoup


soup = TexSoup(r"""
\begin{document}
    \textbf{foo}
    \textit{bar}
\end{document}
""")

textit = soup.find("textit")
other = textit.parent.children[1]

print("Same wrapper:", textit is other)
print("Same parsed expression:", textit.expr is other.expr)

textit.string = "updated"
print("Value through the other wrapper:", other.string)
print("Serialized document contains the edit:", r"\textit{updated}" in str(soup))

repeated = TexSoup(r"\textit{same}\textit{same}")
first, second = repeated.find_all("textit")
print("Repeated equal commands share an expression:", first.expr is second.expr)

separate = TexSoup(r"\textit{same}\textit{same}")
print("Separately parsed documents share an expression:", first.expr is separate.textit.expr)
