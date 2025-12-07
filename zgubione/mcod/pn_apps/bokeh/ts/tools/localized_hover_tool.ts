import {HoverTool, HoverToolView} from "models/tools/inspectors/hover_tool"
import * as p from "core/properties"

export namespace LocalizedHoverTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = HoverTool.Props & {localized_tool_name: p.Property<string>}

}
export interface LocalizedHoverTool extends LocalizedHoverTool.Attrs {}
export class LocalizedHoverTool extends HoverTool{
  properties: LocalizedHoverTool.Props
  __view_type__: HoverToolView


  constructor(attrs?: Partial<HoverTool.Attrs>) {
    super(attrs)
    this.tool_name = this.localized_tool_name
  }

  static init_LocalizedHoverTool(): void {
    this.prototype.default_view = HoverToolView

    this.define<LocalizedHoverTool.Props>({
      localized_tool_name: [ p.String ],
    })
  }
}
