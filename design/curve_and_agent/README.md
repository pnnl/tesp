# Curve and Agent

**Author: Trevor Hardy**

**Last Updated: 3 March 2026**

This folder captures the agent redesign work completed in FY26 to begin the work of re-architecting TESP. That work began with an extended chat between Trevor Hardy and an LLM where the requirements of the agent were progressively disclosed and the LLM produced an increasingly complex software architecture. The prompting of the LLM leveraged experience and Trevor's ideas for how to modularize the functionality of an agent. This conversation was captured in the file named ["chat-💻 Smart Device Market Agent.md"](./chat-💻%20Smart%20Device%20Market%20Agent.md)

The output from that chat was the following:
- A set of PlantUML diagrams showing the structure and expected operation of the agent. These diagrams reside in this folder.
- Documented Python code stubs for the new agent structure. These stubs were turned over to Nathan Gray who used another LLM to implement representative examples; [those example are found in the "src" directory in this repository.](../../src/tesp_support/tesp_support/curve_and_agent/)

Testing of the new agent code was implemented but this testing only verifies functional code and does not verify that the agent performs as expected or desired. 