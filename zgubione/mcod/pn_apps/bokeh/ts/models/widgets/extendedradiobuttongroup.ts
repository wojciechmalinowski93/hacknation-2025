import {ButtonGroup, ButtonGroupView} from "models/widgets/button_group"

import {classes} from "core/dom"
import * as p from "core/properties"

import {bk_active} from "styles/mixins"

export class ExtendedRadioButtonGroupView extends ButtonGroupView {
  model: ExtendedRadioButtonGroup

  render(): void {
    super.render()
    this._buttons.forEach((button) => {
      button.setAttribute('tabindex', "0")
    })
  }

  change_active(i: number): void {
    if (this.model.active !== i) {
      this.model.active = i
    }
  }

  protected _update_active(): void {
    const {active} = this.model

    this._buttons.forEach((button, i) => {
      classes(button).toggle(bk_active, active === i)
    })
  }
}

export namespace ExtendedRadioButtonGroup {
  export type Attrs = p.AttrsOf<Props>

  export type Props = ButtonGroup.Props & {
    active: p.Property<number | null>
  }
}

export interface ExtendedRadioButtonGroup extends ExtendedRadioButtonGroup.Attrs {}

export class ExtendedRadioButtonGroup extends ButtonGroup {
  properties: ExtendedRadioButtonGroup.Props
  __view_type__: ExtendedRadioButtonGroupView

  constructor(attrs?: Partial<ExtendedRadioButtonGroup.Attrs>) {
    super(attrs)
  }

  static init_ExtendedRadioButtonGroup(): void {
    this.prototype.default_view = ExtendedRadioButtonGroupView

    this.define<ExtendedRadioButtonGroup.Props>({
      active: [ p.Any, null ],
    })
  }
}
