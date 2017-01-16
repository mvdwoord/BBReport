# BBReport

Transforms RESAM Building Blocks into a report. The built in report function in RESAM results in a non searchable PDF. This tool strives to create something actually useful. Basic POC done in Powershell with output in Excel through Interop. That turned out to be slow and shit. Benefit would have been editing and color highlighting changes etc built into Excel.

The script parses a building block (xml) file and will create an index file, as well as individual html files for all elements (modules, projects, etc). The will be linked where applicable for easy navigation through a more complex object.
