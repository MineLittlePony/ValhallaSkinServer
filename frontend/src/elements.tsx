import type { AnchorAriaRoles, ComponentChildren, LooseAnchorHTMLAttributes, Signalish } from 'preact'

const buttonClass = 'btn flex items-center justify-center gap-2'

interface LinkProps extends Omit<LooseAnchorHTMLAttributes, 'role'> {
  href: string
  role?: Extract<AnchorAriaRoles, { href: Signalish<string> }>['role']

  icon?: string
  children?: ComponentChildren
}

export function Link({ href, icon, role = 'button', children, ...props }: LinkProps) {
  return (
    <a class={buttonClass} role={role} href={href} {...props}>
      {icon && <div class={icon}></div>}
      <div class={icon && 'sm:block hidden'}>
        {children}
      </div>
    </a>
  )
}
