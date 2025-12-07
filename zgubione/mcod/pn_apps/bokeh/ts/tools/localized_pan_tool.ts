import {PanTool, PanToolView} from "models/tools/gestures/pan_tool"
import * as p from "core/properties"

export namespace LocalizedPanTool {
  export type Attrs = p.AttrsOf<Props>

  export type Props = PanTool.Props & {localized_tool_name: p.Property<string>}

}

export interface LocalizedPanTool extends LocalizedPanTool.Attrs {}

export class LocalizedPanTool extends PanTool{
  properties: LocalizedPanTool.Props
  __view_type__: PanToolView

  constructor(attrs?: Partial<LocalizedPanTool.Attrs>) {
    super(attrs)
    this.tool_name = this.localized_tool_name
  }

  static init_LocalizedPanTool(): void {
    this.prototype.default_view = PanToolView

    this.define<LocalizedPanTool.Props>({
      localized_tool_name: [ p.String ],
    })
  }

  get tooltip(): string {
    return this.tool_name
  }

}
