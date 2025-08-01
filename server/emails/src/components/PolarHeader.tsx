import { Column, Img, Link, Row, Section } from '@react-email/components'

interface HeaderProps {
  featuredOrganization?: {
    name: string
    slug: string
  }
}

const Header = ({ featuredOrganization }: HeaderProps) => (
  <Section className="pt-[10px]">
    <Row>
      <Column className="w-[80%]">
        <Img
          alt="Polar Logo"
          height="42"
          src="https://polar-public-assets.s3.us-east-2.amazonaws.com/emails/polar-logo-blue.png"
        />
      </Column>
      <Column align="right">
        <Row align="right">
          <Column>
            <Link href="https://x.com/polar_sh">
              <Img
                alt="X"
                className="mx-[4px]"
                height="36"
                src="https://polar-public-assets.s3.us-east-2.amazonaws.com/emails/x-logo.png"
                width="36"
              />
            </Link>
          </Column>
          <Column>
            <Link href="https://discord.gg/Pnhfz3UThd">
              <Img
                alt="Discord"
                className="mx-[4px]"
                height="36"
                src="https://polar-public-assets.s3.us-east-2.amazonaws.com/emails/discord-logo.png"
                width="36"
              />
            </Link>
          </Column>
        </Row>
      </Column>
    </Row>
  </Section>
)

export default Header
