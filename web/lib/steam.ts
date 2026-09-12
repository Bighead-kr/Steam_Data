/** The Steam store page for an app id.
 *
 * app_id is the one identifier every record carries, and it's all Steam
 * needs - the slug segment in a canonical store URL is decorative. */
export function steamStoreUrl(appId: number): string {
  return `https://store.steampowered.com/app/${appId}/`;
}
