/** The messages between the chat widget on a host page and the chat page in its iframe (TASK-0143, DEC-0067 decision 7).
 *  ready: frame → host, once loaded. token: host → frame, the stored visitor token or null. save: frame → host, a new
 *  token to store. */
export const MSG = { ready: 'superstep-chat:ready', token: 'superstep-chat:token', save: 'superstep-chat:save' } as const
