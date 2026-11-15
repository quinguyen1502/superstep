import { ArrowRightLeft, Bot, Brain, CirclePlay, Code2, Database, Flag, GitBranch, Layers, Mail, Merge, Plug, Repeat, Scale, Table2, UserCheck, Wrench, type LucideIcon } from 'lucide-react'

export const NODE_ICONS: Record<string, LucideIcon> = {
  start: CirclePlay,
  llm: Brain,
  tool: Wrench,
  condition: GitBranch,
  end: Flag,
  human: UserCheck,
  join: Merge,
  subgraph: Layers,
  mcp: Plug,
  retriever: Database,
  dataset: Table2,
  foreach: Repeat,
  decision: Scale,
  email: Mail,
  code: Code2,
  agent: Bot,
  agent_model: Brain,
  agent_tool: Wrench,
  agent_join: Merge,
  agent_handoff: ArrowRightLeft,
}
// Synthetic exit steps inherit their node's icon, as in the Studio metadata.
NODE_ICONS.subgraph_exit = NODE_ICONS.subgraph
NODE_ICONS.agent_exit = NODE_ICONS.agent
